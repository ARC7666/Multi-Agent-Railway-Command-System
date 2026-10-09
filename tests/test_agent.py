import pytest
from unittest.mock import patch, MagicMock
from agent_system import dispatch_propose_agent, safety_critique_agent, DispatchProposal

@patch('agent_system.get_llm')
def test_dispatch_propose_agent(mock_get_llm):
    mock_llm = MagicMock()
    # Mocking standard LLM output
    mock_llm.invoke.return_value = MagicMock(content='{"reasoning": "delay for safety", "delayed_train_id": "Train1"}')
    mock_get_llm.return_value = mock_llm
    
    state = {
        "trains": [],
        "conflicts": [{"node": "HWH", "trains": ["Train1", "Train2"]}],
        "emergencies": [],
        "llm_reasoning": []
    }
    
    result = dispatch_propose_agent(state)
    assert result["proposed_plan"].delayed_train_id == "Train1"
    assert "delay for safety" in result["proposed_plan"].reasoning

@patch('agent_system.get_llm')
@patch('agent_system.query_safety_manual')
def test_safety_critique_agent(mock_query, mock_get_llm):
    mock_query.return_value = "Trains must be separated by 1 block."
    
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content='{"approved": true, "feedback": ""}')
    mock_get_llm.return_value = mock_llm
    
    state = {
        "trains": [],
        "proposed_plan": DispatchProposal(reasoning="Test", delayed_train_id="Train1"),
        "emergencies": [],
        "llm_reasoning": []
    }
    
    result = safety_critique_agent(state)
    assert result["safety_approved"] is True
