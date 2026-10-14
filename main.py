import os
import asyncio
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from simulation import TrainSimulation
import networkx as nx

EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "https://railway-ai-backend.onrender.com")

async def keep_alive_daemon():
    """
    Self-ping background daemon:
    Periodically sends an external HTTP request to its own public URL to
    ensure the service continuously receives inbound HTTP traffic, resetting
    Render's free-tier 15-minute inactivity timer so the server NEVER goes to sleep.
    """
    await asyncio.sleep(15)
    print(f"[KEEP-ALIVE DAEMON] Activated. Target: {EXTERNAL_URL}")
    while True:
        try:
            # Ping every 7 minutes (420s) - well below Render's 15-minute inactivity limit
            await asyncio.sleep(420)
            if EXTERNAL_URL and not any(h in EXTERNAL_URL for h in ("localhost", "127.0.0.1")):
                ping_url = f"{EXTERNAL_URL.rstrip('/')}/ping"
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.get(ping_url)
                    print(f"[KEEP-ALIVE DAEMON] Keep-alive pulse to {ping_url} -> HTTP {resp.status_code}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[KEEP-ALIVE DAEMON] Pulse notice: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(keep_alive_daemon())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="Railway Simulation API", lifespan=lifespan)

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
        try:
            # Run sim.step() in a worker thread so the event loop is NEVER blocked by AI/I/O
            await asyncio.to_thread(sim.step)
        except Exception as e:
            print(f"[SIMULATION ERROR]: {e}")
        await asyncio.sleep(2)

@app.get("/")
@app.head("/")
def root():
    return {
        "status": "online",
        "service": "Railway Simulation API",
        "keep_alive": "active",
        "endpoints": ["/state", "/ping", "/start", "/stop", "/reset", "/inject_hazard"]
    }

@app.head("/ping")
@app.get("/ping")
def ping():
    return {
        "status": "alive",
        "message": "Render keep-alive successful",
        "is_running": sim.is_running,
        "time_step": sim.time_step,
        "train_count": len(sim.trains)
    }

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
