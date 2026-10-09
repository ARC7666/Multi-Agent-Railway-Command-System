from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from typing import Dict, Any, List, Optional
from simulation import TrainSimulation
import networkx as nx

app = FastAPI(title="Railway Simulation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

sim = TrainSimulation()

class HazardRequest(BaseModel):
    u: str
    v: str
    line: str

@app.get("/state")
def get_state() -> Dict[str, Any]:
    # We need to serialize the network graph because networkx graphs aren't directly JSON serializable
    edges_data = []
    for u, v, d in sim.network.edges(data=True):
        edges_data.append({"u": u, "v": v, "tracks": d.get("tracks", {})})
        
    nodes_data = []
    for node, d in sim.network.nodes(data=True):
        nodes_data.append({"name": node, "lat": d.get("lat"), "lon": d.get("lon")})

    return {
        "trains": sim.trains,
        "time_step": sim.time_step,
        "logs": sim.logs,
        "emergencies": sim.emergencies,
        "hazards": sim.hazards,
        "ai_brain": sim.ai_brain,
        "is_running": sim.is_running,
        "last_ai_action": sim.last_ai_action,
        "last_ai_action_time": sim.last_ai_action_time,
        "network": {
            "nodes": nodes_data,
            "edges": edges_data
        }
    }

async def simulation_loop() -> None:
    while sim.is_running:
        sim.step()
        await asyncio.sleep(2)

@app.get("/ping")
def ping():
    return {"status": "alive", "message": "Render keep-alive successful"}

@app.post("/start")
def start_simulation(background_tasks: BackgroundTasks) -> Dict[str, str]:
    if not sim.is_running:
        sim.is_running = True
        background_tasks.add_task(simulation_loop)
        return {"status": "started"}
    return {"status": "already running"}

@app.post("/stop")
def stop_simulation() -> Dict[str, str]:
    sim.is_running = False
    return {"status": "stopped"}

@app.post("/reset")
def reset_simulation() -> Dict[str, str]:
    sim.is_running = False
    sim.reset()
    return {"status": "reset"}

@app.post("/inject_hazard")
def inject_hazard(req: HazardRequest) -> Dict[str, str]:
    success = sim.inject_hazard(req.u, req.v, req.line)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid hazard injection parameters")
    return {"status": "hazard injected"}
