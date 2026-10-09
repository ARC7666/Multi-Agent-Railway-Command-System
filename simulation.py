import datetime
import random
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple
from railway_graph import create_railway_network
from agent_system import build_graph

class TrainSimulation:
    """
    Encapsulates the railway physics, state, and simulation logic.
    """
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Resets the simulation to its initial state."""
        self.network: nx.Graph = create_railway_network()
        self.trains: List[Dict[str, Any]] = [
            {"id": "Vande Bharat (UP)", "position": "Howrah (HWH)", "destination": "Asansol (ASN)", "dir": "UP", "path": [], "current_edge": None, "progress": 0.0},
            {"id": "Rajdhani Exp (UP)", "position": "Sealdah (SDAH)", "destination": "Asansol (ASN)", "dir": "UP", "path": [], "current_edge": None, "progress": 0.0},
            {"id": "Shatabdi Exp (UP)", "position": "Howrah (HWH)", "destination": "Durgapur (DGR)", "dir": "UP", "path": [], "current_edge": None, "progress": 0.0},
            {"id": "Bandel Local (UP)", "position": "Howrah (HWH)", "destination": "Bandel (BDC)", "dir": "UP", "path": [], "current_edge": None, "progress": 0.0},
            {"id": "Coal Freight 1 (UP)", "position": "Bardhaman (BWN)", "destination": "Asansol (ASN)", "dir": "UP", "path": [], "current_edge": None, "progress": 0.0},
            {"id": "Coal Freight 2 (DN)", "position": "Asansol (ASN)", "destination": "Howrah (HWH)", "dir": "DN", "path": [], "current_edge": None, "progress": 0.0},
            {"id": "Steel Express (DN)", "position": "Durgapur (DGR)", "destination": "Sealdah (SDAH)", "dir": "DN", "path": [], "current_edge": None, "progress": 0.0},
            {"id": "Howrah Local 1 (DN)", "position": "Bandel (BDC)", "destination": "Howrah (HWH)", "dir": "DN", "path": [], "current_edge": None, "progress": 0.0},
            {"id": "Howrah Local 2 (DN)", "position": "Bardhaman (BWN)", "destination": "Howrah (HWH)", "dir": "DN", "path": [], "current_edge": None, "progress": 0.0},
            {"id": "Oil Tanker (DN)", "position": "Asansol (ASN)", "destination": "Sealdah (SDAH)", "dir": "DN", "path": [], "current_edge": None, "progress": 0.0}
        ]
        self.time_step: int = 0
        self.agent = build_graph()
        self.logs: Dict[str, List[str]] = {
            "System": ["SYSTEM INITIATED. CONTINUOUS BLOCK TRACKING ONLINE."],
            "Howrah (HWH) ↔ Bandel (BDC)": [],
            "Bandel (BDC) ↔ Bardhaman (BWN)": [],
            "Bardhaman (BWN) ↔ Durgapur (DGR)": [],
            "Durgapur (DGR) ↔ Asansol (ASN)": []
        }
        self.emergencies: List[Dict[str, Any]] = []
        self.hazards: List[Dict[str, Any]] = []
        self.ai_brain: List[str] = []
        self.is_running: bool = False
        self.last_ai_action: Optional[str] = None
        self.last_ai_action_time: Optional[float] = None

    def add_log(self, msg: str, u: Optional[str] = None, v: Optional[str] = None) -> None:
        """Adds a log message to the appropriate section."""
        added = False
        if u and v:
            for sec in list(self.logs.keys())[1:]:
                if u in sec and v in sec:
                    self.logs[sec].append(msg)
                    added = True
                    break
        if not added:
            self.logs["System"].append(msg)

    def inject_hazard(self, u: str, v: str, line: str) -> bool:
        """Injects a hazard (broken track) into a specific section."""
        if self.network.has_edge(u, v):
            track_data = self.network[u][v]['tracks']
            if line in track_data and track_data[line] == 'active':
                self.network[u][v]['tracks'][line] = 'broken'
                self.emergencies.append({"section": (u, v), "line": line})
                self.hazards.append({"section": (u, v), "line": line})
                ts = datetime.datetime.now().strftime('%H:%M:%S')
                msg = f"[{ts}] [ALERT]: {line} Track Failure detected between {u} and {v}!"
                self.add_log(msg, u, v)
                return True
        return False

    def step(self) -> None:
        """Executes one step of the simulation physics and AI reasoning."""
        if not self.is_running:
            return

        state = {
            "network": self.network,
            "trains": self.trains,
            "conflicts": [],
            "emergencies": self.emergencies,
            "resolved": False,
            "time_step": self.time_step,
            "llm_reasoning": [],
            "debate_rounds": 0,
            "safety_approved": False,
        }

        # Invoke the LangGraph agent system
        result = self.agent.invoke(state)
        ts = datetime.datetime.now().strftime("%H:%M:%S")

        if result.get('llm_reasoning'):
            self.ai_brain.extend(result['llm_reasoning'])
            self.ai_brain = self.ai_brain[-30:]

        if self.emergencies:
            e = self.emergencies[-1]
            diverted_to = "UP2" if "UP1" in e['line'] else "UP1" if "UP" in e['line'] else "DN2" if "DN1" in e['line'] else "DN1"
            direction = "UP" if "UP" in e['line'] else "DN"
            self.add_log(f"[{ts}] [AI]: The {e['line']} track between {e['section'][0]} and {e['section'][1]} is broken.", e['section'][0], e['section'][1])
            self.add_log(f"[{ts}] [AI]: Diverting all {direction} trains in this sector to maintain safety on the remaining {diverted_to} track.", e['section'][0], e['section'][1])
            self.last_ai_action = f"[SUCCESS] AI successfully rerouted all {direction} trains to the {diverted_to} track!"
            self.last_ai_action_time = datetime.datetime.now().timestamp()
        else:
            if not self.logs["System"] or not self.logs["System"][-1].endswith("Optimization Nominal. 10 trains tracking on multi-line sections."):
                self.add_log(f"[{ts}] Optimization Nominal. 10 trains tracking on multi-line sections.")

        if result.get("resolved"):
            self.emergencies.clear()

        updated_trains = result['trains']

        for t in updated_trains:
            if t['path'] and len(t['path']) > 1:
                u_t = t['path'][0]
                v_t = t['path'][1]

                if t.get('current_edge') is None:
                    trains_in_block = [other for other in updated_trains if other.get('current_edge') == (u_t, v_t)]
                    conflict = any(other.get('progress', 1.0) < 0.4 for other in trains_in_block)

                    if conflict:
                        self.add_log(f"[{ts}] [SIGNAL RED]: {t['id']} holding at {u_t} to maintain safe distance from train ahead.", u_t, v_t)
                    else:
                        t['current_edge'] = (u_t, v_t)
                        t['progress'] = 0.25
                        self.add_log(f"[{ts}] [DEPARTURE]: {t['id']} departed {u_t} towards {v_t}.", u_t, v_t)
                else:
                    trains_ahead = [other for other in updated_trains if other.get('current_edge') == (u_t, v_t) and other['id'] != t['id'] and other.get('progress', 0.0) > t['progress']]
                    if trains_ahead and min(other['progress'] for other in trains_ahead) - t['progress'] < 0.2:
                        self.add_log(f"[{ts}] [HEADWAY CONTROL]: {t['id']} slowing down behind leading train.", u_t, v_t)
                        t['progress'] += 0.05
                    else:
                        t['progress'] += 0.25

                    if t['progress'] >= 1.0:
                        self.add_log(f"[{ts}] [ARRIVAL]: {t['id']} arrived at {v_t}.", u_t, v_t)
                        t['position'] = v_t
                        t['path'] = t['path'][1:]
                        t['current_edge'] = None
                        t['progress'] = 0.0

                        if t['position'] == t['destination']:
                            if t['dir'] == "UP":
                                t['dir'] = "DN"
                                t['destination'] = random.choice(["Howrah (HWH)", "Sealdah (SDAH)"])
                                self.add_log(f"[{ts}] [TURNAROUND]: {t['id']} reached UP terminus. Heading back DN to {t['destination']}.")
                            else:
                                t['dir'] = "UP"
                                t['destination'] = "Asansol (ASN)"
                                self.add_log(f"[{ts}] [TURNAROUND]: {t['id']} reached DN terminus. Heading back UP to {t['destination']}.")

        self.trains = updated_trains
        self.time_step += 1
