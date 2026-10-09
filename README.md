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

## Testing
Run the Pytest suite to validate the graph networks and mocked AI agents:
```bash
pytest tests/
```
