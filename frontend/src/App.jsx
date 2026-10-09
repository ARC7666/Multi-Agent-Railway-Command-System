import { useState, useEffect } from 'react';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const stationPos = {
  "Howrah (HWH)": { x: 800, y: 150 },
  "Sealdah (SDAH)": { x: 850, y: 220 },
  "Bandel (BDC)": { x: 600, y: 150 },
  "Bardhaman (BWN)": { x: 400, y: 150 },
  "Durgapur (DGR)": { x: 200, y: 150 },
  "Asansol (ASN)": { x: 50, y: 150 }
};

const trainColors = ['#3b82f6', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f43f5e', '#a855f7', '#fb923c'];

function App() {
  const [state, setState] = useState(null);
  const [error, setError] = useState(false);
  const [selectedSection, setSelectedSection] = useState("");
  const [selectedTrack, setSelectedTrack] = useState("");

  const fetchState = async () => {
    try {
      const res = await fetch(`${API_URL}/state`);
      if (res.ok) {
        const data = await res.json();
        setState(data);
        setError(false);
      } else {
        setError(true);
      }
    } catch (e) {
      setError(true);
    }
  };

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleAction = async (endpoint) => {
    await fetch(`${API_URL}/${endpoint}`, { method: 'POST' });
    fetchState();
  };

  const injectHazard = async () => {
    if (!selectedSection || !selectedTrack) return;
    const [u, v] = selectedSection.split(" ↔ ");
    await fetch(`${API_URL}/inject_hazard`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ u, v, line: selectedTrack })
    });
    fetchState();
  };

  if (error) {
    return <div className="app-container"><h2>Cannot connect to Backend API at {API_URL}</h2></div>;
  }

  if (!state) return <div className="app-container"><h2>Loading Cyber-Physical Network...</h2></div>;

  const totalTracks = state.network.edges.reduce((acc, edge) => acc + Object.keys(edge.tracks).length, 0);
  const brokenTracks = state.network.edges.reduce((acc, edge) => 
    acc + Object.values(edge.tracks).filter(s => s === 'broken').length, 0);
  const health = totalTracks > 0 ? Math.floor(((totalTracks - brokenTracks) / totalTracks) * 100) : 0;

  const sections = Object.keys(state.logs).slice(1);
  const activeSectionEdges = selectedSection ? state.network.edges.find(e => 
    `${e.u} ↔ ${e.v}` === selectedSection || `${e.v} ↔ ${e.u}` === selectedSection
  ) : null;
  const activeLines = activeSectionEdges ? Object.entries(activeSectionEdges.tracks).filter(([k,v]) => v === 'active').map(e => e[0]) : [];

  return (
    <div className="app-container">
      <header className="header">
        <div className="title">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{color: '#3B82F6'}}>
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
            <line x1="8" y1="21" x2="16" y2="21"></line>
            <line x1="12" y1="17" x2="12" y2="21"></line>
          </svg>
          Railway Command Center
          <span className="title-badge">PROD</span>
        </div>
        <div className="controls">
          <button className="btn btn-primary" onClick={() => handleAction('start')}>▶ Start</button>
          <button className="btn btn-danger" onClick={() => handleAction('stop')}>⏸ Stop</button>
          <button className="btn glass-card" onClick={() => handleAction('reset')}>⟲ Reset</button>
        </div>
      </header>

      <div className="kpi-grid">
        <div className="glass-card kpi">
          <div className="kpi-title">System Ticks</div>
          <div className="kpi-value">T+{state.time_step}</div>
        </div>
        <div className="glass-card kpi">
          <div className="kpi-title">Active Trains</div>
          <div className="kpi-value">{state.trains.length}</div>
        </div>
        <div className="glass-card kpi">
          <div className="kpi-title">Track Health</div>
          <div className="kpi-value">{health}%</div>
        </div>
        <div className={`glass-card kpi ${brokenTracks > 0 ? 'alert' : ''}`}>
          <div className="kpi-title">Network Status</div>
          <div className="kpi-value">{brokenTracks > 0 ? `${brokenTracks} BROKEN` : 'NOMINAL'}</div>
        </div>
      </div>

      <div className="glass-card map-container">
        <svg width="100%" height="100%" viewBox="-10 100 920 160">
          {/* Draw Edges */}
          {state.network.edges.map((edge, idx) => {
            const posU = stationPos[edge.u];
            const posV = stationPos[edge.v];
            if (!posU || !posV) return null;
            return (
              <line 
                key={idx} x1={posU.x} y1={posU.y} x2={posV.x} y2={posV.y} 
                stroke="#334155" strokeWidth="4" 
              />
            );
          })}
          
          {/* Draw Hazards */}
          {state.hazards.map((h, i) => {
            const posU = stationPos[h.section[0]];
            const posV = stationPos[h.section[1]];
            if (!posU || !posV) return null;
            const hx = (posU.x + posV.x) / 2;
            const hy = (posU.y + posV.y) / 2;
            return (
              <g key={`h-${i}`}>
                <circle cx={hx} cy={hy} r="12" fill="rgba(239, 68, 68, 0.2)" className="pulse" />
                <text x={hx} y={hy+4} fill="#EF4444" fontSize="16" textAnchor="middle" fontWeight="bold">X</text>
              </g>
            );
          })}

          {/* Draw Nodes */}
          {state.network.nodes.map((node, idx) => {
            const pos = stationPos[node.name];
            if (!pos) return null;
            return (
              <g key={idx}>
                <circle cx={pos.x} cy={pos.y} r="8" fill="#1E293B" stroke="#3B82F6" strokeWidth="3" />
                <text x={pos.x} y={pos.y - 15} fill="#94A3B8" fontSize="11" textAnchor="middle">{node.name}</text>
              </g>
            );
          })}

          {/* Draw Trains */}
          {state.trains.map((train, idx) => {
            let x = 0, y = 0;
            if (train.current_edge) {
              const posU = stationPos[train.current_edge[0]];
              const posV = stationPos[train.current_edge[1]];
              if (posU && posV) {
                x = posU.x + (posV.x - posU.x) * train.progress;
                y = posU.y + (posV.y - posU.y) * train.progress;
                y += train.dir === "UP" ? -8 : 8; // Offset tracks visually
              }
            } else {
              const pos = stationPos[train.position];
              if (pos) {
                x = pos.x + (idx % 3 - 1) * 12;
                y = pos.y + (Math.floor(idx / 3) % 3 - 1) * 12;
              }
            }
            return (
              <g key={train.id} className="train-node" style={{transform: `translate(${x}px, ${y}px)`}}>
                <circle cx="0" cy="0" r="7" fill={trainColors[idx % trainColors.length]} />
                <text x="0" y="15" fill="#F8FAFC" fontSize="9" textAnchor="middle">{train.id.split(' ')[0]}</text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="main-content">
        {/* Column 1: AI Brain */}
        <div className="glass-card">
          <h3 style={{marginBottom: '1rem', color: '#94A3B8'}}>AI Multi-Agent Reasoning Brain</h3>
          <div className="ai-brain" style={{height: '350px'}}>
            {state.ai_brain.slice().reverse().map((log, i) => {
              let typeClass = '';
              if (log.includes("[DISPATCHER]")) typeClass = 'ai-dispatcher';
              else if (log.includes("[SAFETY INSPECTOR]")) typeClass = 'ai-safety';
              else if (log.includes("[RAG]")) typeClass = 'ai-rag';
              
              return <div key={i} className={`ai-entry ${typeClass}`}>{log}</div>;
            })}
            {state.ai_brain.length === 0 && <div style={{color: '#64748B', fontStyle: 'italic', padding: '1rem'}}>AI Agents standing by...</div>}
          </div>
        </div>

        {/* Column 2: Live Section Status */}
        <div className="glass-card">
          <h3 style={{marginBottom: '1rem', color: '#94A3B8'}}>Live Section Status</h3>
          <div className="logs-container" style={{height: '350px'}}>
            {sections.map(sec => {
              const [u, v] = sec.split(" ↔ ");
              const trainsInSection = state.trains.filter(t => t.current_edge && (
                (t.current_edge[0] === u && t.current_edge[1] === v) || 
                (t.current_edge[0] === v && t.current_edge[1] === u)
              ));
              
              return (
                <div key={sec} style={{marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)'}}>
                  <div style={{fontWeight: 'bold', color: '#60A5FA', marginBottom: '0.5rem'}}>{sec}</div>
                  {trainsInSection.length > 0 ? (
                    trainsInSection.map(t => (
                      <div key={t.id} style={{display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px'}}>
                        <span style={{display: 'flex', alignItems: 'center'}}>
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{marginRight: '6px', color: '#94A3B8'}}><rect width="16" height="16" x="4" y="3" rx="2"/><path d="M4 11h16"/><path d="M12 3v8"/><path d="m8 19-2 3"/><path d="m16 19 2 3"/><path d="M8 15h.01"/><path d="M16 15h.01"/></svg>
                          {t.id}
                        </span>
                        <span style={{color: '#10B981'}}>{Math.round(t.progress * 100)}% through block</span>
                      </div>
                    ))
                  ) : (
                    <div style={{color: '#64748B', fontSize: '0.85rem', fontStyle: 'italic'}}>No active trains in section</div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Column 3: Hazard Injection & Logs */}
        <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
          <div className="glass-card hazard-panel" style={{marginTop: 0}}>
            <h3 style={{marginBottom: '1rem', color: '#EF4444'}}>Inject Track Failure</h3>
            <select className="select-input" value={selectedSection} onChange={e => {setSelectedSection(e.target.value); setSelectedTrack("");}}>
              <option value="">-- Select Section --</option>
              {sections.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            
            {selectedSection && (
              <select className="select-input" value={selectedTrack} onChange={e => setSelectedTrack(e.target.value)}>
                <option value="">-- Select Track --</option>
                {activeLines.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
            )}
            
            <button className="btn btn-danger" style={{width: '100%', justifyContent: 'center', display: 'flex', alignItems: 'center', gap: '0.5rem'}} onClick={injectHazard} disabled={!selectedTrack}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
              Break Track
            </button>
          </div>
          
          <div className="glass-card" style={{flex: 1}}>
             <h3 style={{marginBottom: '1rem', color: '#94A3B8'}}>System Logs</h3>
             <div className="logs-container" style={{height: '140px'}}>
               {state.logs["System"].slice().reverse().slice(0, 15).map((log, i) => {
                 const timeMatch = log.match(/^\[(.*?)\] (.*)/);
                 if (timeMatch) {
                   return (
                     <div key={i} className="log-entry">
                       <span className="log-time">{timeMatch[1]}</span>
                       <span>{timeMatch[2]}</span>
                     </div>
                   );
                 }
                 return <div key={i} className="log-entry">{log}</div>;
               })}
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
