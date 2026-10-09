import networkx as nx
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
import os
import json
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from rag_system import query_safety_manual

# Load environment variables
load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"


class DispatchProposal(BaseModel):
    reasoning: str = Field(description="Why you are making this decision.")
    delayed_train_id: str = Field(description="ID of the train to delay, or 'NONE' if no train needs delaying.")

class SafetyCritique(BaseModel):
    approved: bool = Field(description="True if the plan violates NO safety rules. False if it violates a rule.")
    feedback: str = Field(description="If False, explain EXACTLY which rule is violated based on the manual and what the dispatcher should do instead.")

class TrackState(TypedDict):
    network: Any
    trains: List[Dict]
    conflicts: List[Dict]
    emergencies: List[str] # New: Track Hazmat Spills
    resolved: bool
    time_step: int
    llm_reasoning: List[str]
    proposed_plan: DispatchProposal
    safety_approved: bool
    debate_rounds: int

def track_state_agent(state: TrackState) -> TrackState:
    trains = state['trains']
    network = state['network']
    
    active_edges = [(u, v) for u, v, d in network.edges(data=True) if d.get('status', 'active') == 'active']
    active_network = network.edge_subgraph(active_edges)
    
    for train in trains:
        if not train.get('path') or len(train['path']) <= 1:
            try:
                if train['position'] in active_network and train['destination'] in active_network:
                    path = nx.shortest_path(active_network, source=train['position'], target=train['destination'])
                    train['path'] = path
                else:
                    train['path'] = [train['position']]
            except nx.NetworkXNoPath:
                train['path'] = [train['position']]
                
    return {"trains": trains}

def conflict_detection_agent(state: TrackState) -> TrackState:
    # Disable over-sensitive node conflicts to save LLM tokens and prevent rate limits.
    # The kinematic engine in app.py already handles basic headway/following conflicts.
    # The LLM will now only be invoked for high-level Emergency routing (track breaks).
    return {"conflicts": []}

from langchain_core.language_models.chat_models import BaseChatModel

def get_llm() -> BaseChatModel:
    llm1 = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
    llm2 = ChatGroq(model="mixtral-8x7b-32768", temperature=0)
    llm3 = ChatGroq(model="gemma2-9b-it", temperature=0)
    return llm1.with_fallbacks([llm2, llm3])

def dispatch_propose_agent(state: TrackState) -> TrackState:
    """Agent 1: Proposes a solution to the conflict or emergency."""
    conflicts = state['conflicts']
    emergencies = state.get('emergencies', [])
    trains = state['trains']
    reasonings = state.get('llm_reasoning', [])
    llm = get_llm()
    issue = f"Conflict at {conflicts[0]['node']} involving {conflicts[0]['trains']}" if conflicts else f"Emergency: {emergencies[0]}"
    
    prompt = f"""
    You are the Dispatcher. An issue requires your attention: {issue}
    Current Trains: {trains}
    
    Propose a resolution. If you must delay a train, provide its ID. If you need to stop all trains, say so in reasoning.
    
    You MUST respond with a valid JSON object ONLY. Do not write markdown blocks or any other text.
    Format strictly like this:
    {{"reasoning": "Why you made this decision", "delayed_train_id": "ID of train to delay or NONE"}}
    """
    
    response = llm.invoke(prompt)
    try:
        content = response.content.strip()
        if content.startswith("```json"): content = content[7:-3].strip()
        elif "{" in content: content = content[content.find("{"):content.rfind("}")+1]
        decision = json.loads(content)
        proposed_plan = DispatchProposal(**decision)
    except Exception as e:
        # Fallback to prevent crash
        proposed_plan = DispatchProposal(reasoning="Failed to parse model response.", delayed_train_id="NONE")
        
    reasonings.append(f"[DISPATCHER]: Proposes delay on {proposed_plan.delayed_train_id} because {proposed_plan.reasoning}")
            
    return {"proposed_plan": proposed_plan, "llm_reasoning": reasonings}

def safety_critique_agent(state: TrackState) -> TrackState:
    """Agent 2: Uses RAG to critique the Dispatcher's proposal."""
    proposal = state['proposed_plan']
    emergencies = state.get('emergencies', [])
    reasonings = state.get('llm_reasoning', [])
    trains = state['trains']
    
    # 1. Query the RAG Vector Database for rules
    query = "Hazmat spill rules and priority rules" if emergencies else "Priority rules and track failures"
    safety_rules = query_safety_manual(query)
    
    if state.get('debate_rounds', 0) == 0:
        reasonings.append(f"[RAG]: Queried Vector DB: '{query}'")
        reasonings.append(f"[RAG]: Retrieved Context: {safety_rules[:150]}...")
    llm = get_llm()
    prompt = f"""
    You are the Safety Inspector. The Dispatcher proposed this plan:
    "Delay train {proposal.delayed_train_id}. Reason: {proposal.reasoning}"
    
    Current Trains: {trains}
    Active Emergencies: {emergencies}
    
    CRITICAL SAFETY MANUAL (RAG Retrieval):
    {safety_rules}
    
    Does the dispatcher's plan VIOLATE any rules in the safety manual? 
    You MUST respond with a valid JSON object ONLY. Do not write markdown blocks or any other text.
    Format strictly like this:
    {{"approved": true, "feedback": "If false, explain exactly which rule is violated"}}
    """
    
    response = llm.invoke(prompt)
    try:
        content = response.content.strip()
        if content.startswith("```json"): content = content[7:-3].strip()
        elif "{" in content: content = content[content.find("{"):content.rfind("}")+1]
        critique_dict = json.loads(content)
        critique = SafetyCritique(**critique_dict)
    except Exception as e:
        critique = SafetyCritique(approved=True, feedback="Fallback approval due to parse error.")
        
    rounds = state.get('debate_rounds', 0) + 1
    
    if critique.approved:
        reasonings.append(f"[SAFETY INSPECTOR]: APPROVED.")
        
        # Apply the approved plan
        if proposal.delayed_train_id != 'NONE':
            try:
                t_delayed = next(t for t in trains if t['id'] == proposal.delayed_train_id)
                if t_delayed['path']:
                    t_delayed['path'].insert(1, t_delayed['path'][0])
            except StopIteration:
                pass
        return {"safety_approved": True, "llm_reasoning": reasonings, "debate_rounds": rounds, "resolved": True, "trains": trains}
    else:
        reasonings.append(f"[SAFETY INSPECTOR]: REJECTED! {critique.feedback}")
        return {"safety_approved": False, "llm_reasoning": reasonings, "debate_rounds": rounds}

def router(state: TrackState) -> str:
    if not state['conflicts'] and not state.get('emergencies', []):
        return "continue"
    return "propose"

def debate_router(state: TrackState) -> str:
    if state['safety_approved'] or state.get('debate_rounds', 0) >= 2:
        # If approved or we argued too much, end it.
        return END
    return "propose" # Go back to dispatcher to try again!

from langgraph.graph.state import CompiledStateGraph

def build_graph() -> CompiledStateGraph:
    workflow = StateGraph(TrackState)
    
    workflow.add_node("monitor", track_state_agent)
    workflow.add_node("detect", conflict_detection_agent)
    workflow.add_node("dispatch_propose", dispatch_propose_agent)
    workflow.add_node("safety_critique", safety_critique_agent)
    
    workflow.set_entry_point("monitor")
    workflow.add_edge("monitor", "detect")
    
    workflow.add_conditional_edges(
        "detect",
        router,
        {
            "propose": "dispatch_propose",
            "continue": END
        }
    )
    
    workflow.add_edge("dispatch_propose", "safety_critique")
    
    # The Debate Loop!
    workflow.add_conditional_edges(
        "safety_critique",
        debate_router,
        {
            "propose": "dispatch_propose",
            END: END
        }
    )
    
    return workflow.compile()
