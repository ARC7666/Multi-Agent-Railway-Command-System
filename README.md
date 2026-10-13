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

## Deployment & Render Free-Tier Keep-Alive

### Preventing 1-Minute Cold Starts on Render Free Tier
Render free-tier web services automatically spin down after 15 minutes of inactivity. When a request arrives, Render takes 45–50 seconds to boot the Python environment.

We have addressed this on multiple levels:
1. **Frontend Smart Radar Screen**: The UI detects cold start, shows an animated radar and progress indicator, and auto-retries telemetry.
2. **Frontend Keep-Alive Heartbeat**: While any user keeps the dashboard open in a browser tab, a background heartbeat pings `/ping` every 3 minutes.
3. **Automated 24/7 Keep-Alive (Zero Downtime)**:
   - A GitHub Actions workflow [`.github/workflows/render_keep_alive.yml`](file:///Users/ankitranjan/Documents/railway%20ml%20project/.github/workflows/render_keep_alive.yml) runs every 14 minutes. Add `RENDER_BACKEND_URL` to your GitHub repository secrets (or update the default URL in the workflow).
   - Alternatively, add your `/ping` URL (e.g. `https://your-service.onrender.com/ping`) to a free monitoring service like [cron-job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com) with a 10–14 minute interval.

## Multi-Agent AI System Architecture
- **Dispatcher Agent**: Evaluates track hazards and dynamically calculates alternative routing on parallel tracks.
- **Safety Inspector Agent (RAG)**: Uses BM25 retrieval against [safety_manual.txt](file:///Users/ankitranjan/Documents/railway%20ml%20project/safety_manual.txt) to validate proposed routing plans.
- **Fail-Safe Fallbacks**: Uses `qwen/qwen3.8-27b` on Groq (~0.3s response time) with fallbacks to `openai/gpt-oss-20b` and deterministic fail-safe emergency protocols so the simulation never freezes or crashes.

## Testing
Run the Pytest suite to validate the graph networks and mocked AI agents:
```bash
pytest tests/
```
