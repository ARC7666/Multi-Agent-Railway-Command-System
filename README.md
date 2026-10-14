# Multi-Track AI Autonomous Railway Command System

An advanced cyber-physical system using Multi-Agent AI to manage and dispatch trains across a complex multi-track railway network in real-time.

## Features
- **Multi-Agent Orchestration**: Uses LangGraph to create a debate loop between a Dispatcher AI and a Safety Inspector AI.
- **Retrieval-Augmented Generation (RAG)**: The Safety Inspector grounds its decisions by retrieving rules from a local `safety_manual.txt` using ChromaDB and HuggingFace embeddings.
- **Physical Modeling**: Simulates a 6-station, 4-track network with 10 simultaneous trains using NetworkX.
- **Clean Architecture**: Decoupled FastAPI backend and Streamlit frontend.

## Getting Started

1. Create a `.env` file and add your `GROQ_API_KEY`:
```
GROQ_API_KEY=your_key_here
```

2. Start the FastAPI Backend:
```bash
source venv/bin/activate
fastapi dev main.py
```

3. Start the Streamlit UI (in a new terminal):
```bash
source venv/bin/activate
streamlit run app.py
```

## 24/7 High-Availability & Keep-Alive Architecture

To guarantee the backend runs with zero cold starts and never spins down, a 4-tier keep-alive system is implemented:

1. **Internal Self-Ping Daemon (`main.py`)**: Runs continuously as an async background task inside FastAPI's lifespan, pinging its own external URL (`https://railway-ai-backend.onrender.com/ping`) every 7 minutes, continually resetting Render's 15-minute inactivity idle timer.
2. **GitHub Actions 5-Minute Pinger (`.github/workflows/render_keep_alive.yml`)**: Automated cron runs every 5 minutes with retry logic, ensuring active traffic even if an instance reboots.
3. **Dedicated 24/7 External Ping (UptimeRobot / Cron-Job.org)**: Add `https://railway-ai-backend.onrender.com/ping` to [cron-job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com) (HTTP GET every 5 or 10 minutes) for 100% guaranteed 24/7/365 uptime.
4. **Browser Heartbeat**: Active dashboard clients ping `/ping` every 2 minutes to keep telemetry streaming in real time.

## Multi-Agent AI System Architecture
- **Dispatcher Agent**: Evaluates track hazards and dynamically calculates alternative routing on parallel tracks.
- **Safety Inspector Agent (RAG)**: Uses BM25 retrieval against [safety_manual.txt](file:///Users/ankitranjan/Documents/railway%20ml%20project/safety_manual.txt) to validate proposed routing plans.
- **Fail-Safe Fallbacks**: Uses `qwen/qwen3.8-27b` on Groq (~0.3s response time) with fallbacks to `openai/gpt-oss-20b` and deterministic fail-safe emergency protocols so the simulation never freezes or crashes.

## Testing
Run the Pytest suite to validate the graph networks and mocked AI agents:
```bash
pytest tests/
```
