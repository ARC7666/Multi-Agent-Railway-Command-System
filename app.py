import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import requests
import time
import datetime

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Multi-Track AI Command", page_icon="🚆", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e2e8f0; }
    .kpi-card { background: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6; margin-bottom: 15px;}
    .alert-card { border-left: 4px solid #ef4444; }
    .kpi-title { font-size: 14px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 28px; font-weight: bold; color: #f8fafc; }
    .log-window { background: #1e293b; border: 1px solid #475569; border-radius: 8px; padding: 15px; font-family: 'Inter', sans-serif; font-size: 14px; height: 300px; overflow-y: auto; color: #e2e8f0; line-height: 1.6; }
    .log-entry { margin-bottom: 12px; border-bottom: 1px solid #334155; padding-bottom: 8px; }
    .log-time { color: #94a3b8; font-size: 12px; margin-right: 8px; font-family: 'Courier New', monospace; }
</style>
""", unsafe_allow_html=True)

# Fetch state
try:
    response = requests.get(f"{API_URL}/state")
    if response.status_code == 200:
        state = response.json()
    else:
        st.error("Failed to fetch state from backend.")
        st.stop()
except requests.exceptions.ConnectionError:
    st.error("Cannot connect to the backend server. Make sure FastAPI is running at 127.0.0.1:8000.")
    st.stop()

# Reconstruct networkx graph for visualization
network_data = state.get("network", {})
network = nx.Graph()
for node in network_data.get("nodes", []):
    network.add_node(node["name"], lat=node["lat"], lon=node["lon"])
for edge in network_data.get("edges", []):
    network.add_edge(edge["u"], edge["v"], tracks=edge["tracks"])

with st.sidebar:
    st.title("Hazard Injection Panel")
    st.write("Simulate a track breakdown in a specific section.")
    
    sections = list(state["logs"].keys())[1:] if len(state["logs"]) > 1 else []
    
    if sections:
        selected_section = st.selectbox("Select Network Section:", sections)
        u, v = selected_section.split(" ↔ ")
        
        if network.has_edge(u, v):
            track_data = network[u][v].get('tracks', {})
            active_lines = [line for line, status in track_data.items() if status == 'active']
            
            if active_lines:
                selected_line = st.selectbox("Select Specific Track to Break:", active_lines)
                if st.button("Break Track", type="primary"):
                    requests.post(f"{API_URL}/inject_hazard", json={"u": u, "v": v, "line": selected_line})
                    st.rerun()
            else:
                st.error("All tracks in this section are broken!")
                
    st.markdown("---")
    if st.button("Hard Reset Simulation", use_container_width=True):
        requests.post(f"{API_URL}/reset")
        st.rerun()

st.title("Multi-Track AI Autonomous Routing")

col_start, col_stop = st.columns(2)
if col_start.button("Start Simulation", type="primary", use_container_width=True):
    requests.post(f"{API_URL}/start")
    st.rerun()
if col_stop.button("Stop Simulation", use_container_width=True):
    requests.post(f"{API_URL}/stop")
    st.rerun()

# --- TOP KPIS ---
k1, k2, k3, k4 = st.columns(4)
k1.markdown(f"<div class='kpi-card'><div class='kpi-title'>System Ticks</div><div class='kpi-value'>T+{state['time_step']}</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='kpi-card'><div class='kpi-title'>Active Trains</div><div class='kpi-value'>{len(state['trains'])}</div></div>", unsafe_allow_html=True)

total_tracks = sum(len(d.get('tracks', {})) for _u, _v, d in network.edges(data=True))
broken_tracks = sum(1 for _u, _v, d in network.edges(data=True) for status in d.get('tracks', {}).values() if status == 'broken')
health = int(((total_tracks - broken_tracks) / total_tracks) * 100) if total_tracks > 0 else 0
k3.markdown(f"<div class='kpi-card'><div class='kpi-title'>Track Health</div><div class='kpi-value'>{health}%</div></div>", unsafe_allow_html=True)

status_class = "alert-card" if broken_tracks > 0 else ""
status_text = f"{broken_tracks} TRACKS COMPROMISED" if broken_tracks > 0 else "NOMINAL"
k4.markdown(f"<div class='kpi-card {status_class}'><div class='kpi-title'>Network Status</div><div class='kpi-value'>{status_text}</div></div>", unsafe_allow_html=True)

if state.get('last_ai_action'):
    if state.get('last_ai_action_time'):
        elapsed = datetime.datetime.now().timestamp() - state['last_ai_action_time']
        if elapsed < 5:
            st.success(state['last_ai_action'])

def plot_complex_graph():
    pos = {node: (data.get('lon', 0), data.get('lat', 0)) for node, data in network.nodes(data=True)}
    
    fig, ax = plt.subplots(figsize=(16, 4)) 
    fig.patch.set_alpha(0.0) 
    ax.patch.set_alpha(0.0)
    
    nx.draw_networkx_edges(network, pos, ax=ax, edge_color='#334155', width=3)
    
    for hazard in state.get('hazards', []):
        u_h, v_h = hazard['section']
        if u_h in pos and v_h in pos:
            x = (pos[u_h][0] + pos[v_h][0]) / 2
            y = (pos[u_h][1] + pos[v_h][1]) / 2
            ax.plot(x, y, marker='X', markersize=20, color='#ef4444')
            ax.text(x, y+0.03, "TRACK BROKEN", color='#ef4444', fontsize=10, ha='center', weight='bold')

    nx.draw_networkx_nodes(network, pos, ax=ax, node_color='#1e293b', node_size=600, edgecolors='#3b82f6', linewidths=2)
    nx.draw_networkx_labels(network, pos, ax=ax, font_size=9, font_color='#e2e8f0')
    
    colors = ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f43f5e', '#a855f7', '#fb923c']
    for idx, train in enumerate(state.get('trains', [])):
        color = colors[idx % len(colors)]
        if train.get('current_edge') is not None:
            u_t, v_t = train['current_edge']
            u_pos = pos.get(u_t, (0,0))
            v_pos = pos.get(v_t, (0,0))
            progress = train.get('progress', 0.5)
            offset_x = 0.015 if train.get('dir') == "UP" else -0.015
            offset_y = 0.015 if train.get('dir') == "UP" else -0.015
            x = u_pos[0] + (v_pos[0] - u_pos[0]) * progress + offset_x
            y = u_pos[1] + (v_pos[1] - u_pos[1]) * progress + offset_y
        else:
            train_pos = train.get('position')
            offset_x = (idx % 3 - 1) * 0.015 
            offset_y = ((idx // 3) % 3 - 1) * 0.015
            train_coords = pos.get(train_pos, (0,0))
            x = train_coords[0] + offset_x
            y = train_coords[1] + offset_y
            
        ax.plot(x, y, marker='o', markersize=14, color=color, markeredgecolor='#ffffff', label=f"{train.get('id')}")
        
    ax.set_axis_off()
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=9, frameon=False, labelcolor='#e2e8f0')
    plt.tight_layout()
    return fig
    
st.pyplot(plot_complex_graph())

st.markdown("---")
# --- TABBED LOGS ---
tab1, tab2 = st.tabs(["System Activity Logs by Section", "Agentic AI Brain & Hazard RAG"])

with tab1:
    logs = state.get("logs", {})
    sec_tabs = st.tabs(list(logs.keys())) if logs else []
    for idx, sec_name in enumerate(logs.keys()):
        with sec_tabs[idx]:
            formatted_logs = []
            for log in reversed(logs[sec_name]):
                if log.startswith("["):
                    time_part = log[0:10]
                    msg_part = log[11:]
                    formatted_logs.append(f"<div class='log-entry'><span class='log-time'>{time_part}</span> {msg_part}</div>")
                else:
                    formatted_logs.append(f"<div class='log-entry'>{log}</div>")
                    
            log_content = "".join(formatted_logs) if formatted_logs else "<div style='color:#64748b; font-style:italic;'>No activity in this section.</div>"
            st.markdown(f"<div class='log-window'>{log_content}</div>", unsafe_allow_html=True)

with tab2:
    st.markdown("<div style='color:#94a3b8; font-size:13px; margin-bottom:10px;'>Live stream of the multi-agent debate and RAG retrieval when resolving hazards:</div>", unsafe_allow_html=True)
    brain_logs = []
    for line in reversed(state.get("ai_brain", [])):
        color = "#f8fafc"
        if "[DISPATCHER]" in line: color = "#3b82f6"
        elif "[SAFETY INSPECTOR]" in line: color = "#ef4444"
        elif "[RAG]" in line: color = "#10b981"
        brain_logs.append(f"<div style='margin-bottom:8px; border-left:3px solid {color}; padding-left:10px; color:#e2e8f0; font-size:13px; font-family:monospace;'>{line}</div>")
        
    brain_content = "".join(brain_logs)
    if not brain_content:
        brain_content = "<div style='color:#64748b; font-style:italic;'>No active hazards. AI agents are standing by...</div>"
    st.markdown(f"<div class='log-window' style='background:#0f172a; border-color:#3b82f6;'>{brain_content}</div>", unsafe_allow_html=True)

if state.get("is_running"):
    time.sleep(2)
    st.rerun()
