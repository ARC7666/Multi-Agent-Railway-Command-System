import { useState, useEffect, useRef } from 'react';
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

const trainColors = [
  '#3b82f6', '#f59e0b', '#10b981', '#ef4444', 
  '#8b5cf6', '#ec4899', '#14b8a6', '#f43f5e', 
  '#a855f7', '#fb923c'
];

function App() {
  const [state, setState] = useState(null);
  const [isWakingUp, setIsWakingUp] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [elapsedWait, setElapsedWait] = useState(0);
  const [selectedSection, setSelectedSection] = useState("");
  const [selectedTrack, setSelectedTrack] = useState("");
  const [isInjecting, setIsInjecting] = useState(false);
  const [actionPending, setActionPending] = useState(null);
  const [aiDebating, setAiDebating] = useState(false);

  const initialLoadTimeRef = useRef(Date.now());

  // Fetch current simulation and network state
  const fetchState = async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 6000);
      const res = await fetch(`${API_URL}/state`, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        setState(data);
        setIsWakingUp(false);
        setReconnecting(false);
      } else {
        if (!state) {
          setIsWakingUp(true);
        } else {
          setReconnecting(true);
        }
      }
    } catch (e) {
      if (!state) {
        setIsWakingUp(true);
      } else {
        setReconnecting(true);
      }
    }
  };

  // Initial poll and recurring poll
  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 1000);
    return () => clearInterval(interval);
  }, []);

  // Timer while waiting for backend cold start
  useEffect(() => {
    if (state) return;
    const timer = setInterval(() => {
      setElapsedWait(Math.floor((Date.now() - initialLoadTimeRef.current) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [state]);

  // Keep-alive background ping every 3 minutes while tab is active
  useEffect(() => {
    const pingInterval = setInterval(() => {
      fetch(`${API_URL}/ping`).catch(() => {});
    }, 3 * 60 * 1000);
    return () => clearInterval(pingInterval);
  }, []);

  const handleAction = async (endpoint) => {
    try {
      setActionPending(endpoint);
      await fetch(`${API_URL}/${endpoint}`, { method: 'POST' });
    } catch (e) {
      console.error(`Failed action ${endpoint}:`, e);
    } finally {
      setActionPending(null);
      await fetchState();
    }
  };

  const injectHazard = async () => {
    if (!selectedSection || !selectedTrack || isInjecting) return;
    const [u, v] = selectedSection.split(" ↔ ");
    setIsInjecting(true);
    setAiDebating(true);
    try {
      const res = await fetch(`${API_URL}/inject_hazard`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ u, v, line: selectedTrack })
      });
      if (res.ok) {
        setSelectedTrack("");
      }
    } catch (e) {
      console.error("Failed to inject hazard:", e);
    } finally {
      setIsInjecting(false);
      await fetchState();
      // Keep AI active highlight for 3 seconds to let user observe
      setTimeout(() => setAiDebating(false), 3000);
    }
  };

  // Render Cold Start / Loading Screen with rich status and diagnostics
  if (!state) {
    const progressPercent = Math.min(100, Math.floor((elapsedWait / 50) * 100));
    return (
      <div className="waking-wrapper">
        <div className="glass-card waking-card">
          <div className="radar-container">
            <div className="radar-circle"></div>
            <div className="radar-sweep"></div>
            <span className="radar-icon">🚆</span>
          </div>

          <h2 className="waking-title">Autonomous Railway Command System</h2>
          <p className="waking-subtitle">
            {elapsedWait > 4 
              ? "Waking up server from Render free-tier standby..." 
              : "Connecting to Cyber-Physical Railway Network..."}
          </p>

          <div className="waking-progress-box">
            <div className="progress-bar-bg">
              <div 
                className="progress-bar-fill" 
                style={{ width: `${Math.max(5, progressPercent)}%` }}
              ></div>
            </div>
            <div className="waking-meta">
              <span>Status: Establishing Telemetry Stream</span>
              <span>Elapsed: {elapsedWait}s / ~50s</span>
            </div>
          </div>

          {elapsedWait > 4 && (
            <div className="waking-info-alert">
              <strong>ℹ️ Render Free-Tier Notice:</strong>
              <p>
                Render automatically sleeps free instances after 15 minutes of inactivity. 
                Initial boot takes 45–50 seconds. Once awake, the command center runs in real-time.
              </p>
            </div>
          )}

          <div className="waking-actions">
            <button className="btn btn-primary" onClick={fetchState}>
              🔄 Check Connection Now
            </button>
            <span className="backend-tag">Target: {API_URL}</span>
          </div>
        </div>
      </div>
    );
  }

  const totalTracks = state.network.edges.reduce((acc, edge) => acc + Object.keys(edge.tracks).length, 0);
  const brokenTracks = state.network.edges.reduce((acc, edge) => 
    acc + Object.values(edge.tracks).filter(s => s === 'broken').length, 0);
  const health = totalTracks > 0 ? Math.floor(((totalTracks - brokenTracks) / totalTracks) * 100) : 0;

  const sections = Object.keys(state.logs).slice(1);
  const activeSectionEdges = selectedSection ? state.network.edges.find(e => 
    `${e.u} ↔ ${e.v}` === selectedSection || `${e.v} ↔ ${e.u}` === selectedSection
  ) : null;
  const activeLines = activeSectionEdges ? Object.entries(activeSectionEdges.tracks).filter(([, v]) => v === 'active').map(e => e[0]) : [];

  return (
    <div className="app-container">
      {/* Reconnecting banner if telemetry dropped transiently */}
      {reconnecting && (
        <div className="reconnecting-banner">
          <span>📡 Syncing live telemetry with backend...</span>
        </div>
      )}

      <header className="header">
        <div className="title">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{color: '#3B82F6'}}>
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
            <line x1="8" y1="21" x2="16" y2="21"></line>
            <line x1="12" y1="17" x2="12" y2="21"></line>
          </svg>
          Railway Command Center
          <span className="title-badge">MULTI-AGENT AI</span>
          <span className={`sim-state-chip ${state.is_running ? 'running' : 'paused'}`}>
            {state.is_running ? '● SIMULATION RUNNING' : '⏸ SIMULATION PAUSED'}
          </span>
        </div>
        <div className="controls">
          <button 
            className="btn btn-primary" 
            disabled={actionPending === 'start' || state.is_running} 
            onClick={() => handleAction('start')}
          >
            {actionPending === 'start' ? 'Starting...' : '▶ Start'}
          </button>
          <button 
            className="btn btn-danger" 
            disabled={actionPending === 'stop' || !state.is_running} 
            onClick={() => handleAction('stop')}
          >
            {actionPending === 'stop' ? 'Stopping...' : '⏸ Stop'}
          </button>
          <button 
            className="btn glass-card" 
            disabled={actionPending === 'reset'} 
            onClick={() => handleAction('reset')}
          >
            {actionPending === 'reset' ? 'Resetting...' : '⟲ Reset'}
          </button>
        </div>
      </header>

      {/* AI Action Banner */}
      {state.last_ai_action && (
        <div className="ai-success-banner">
          <span className="banner-icon">🛡️</span>
          <span>{state.last_ai_action}</span>
        </div>
      )}

      <div className="kpi-grid">
        <div className="glass-card kpi">
          <div className="kpi-title">System Ticks</div>
          <div className="kpi-value">T+{state.time_step}</div>
        </div>
        <div className="glass-card kpi">
          <div className="kpi-title">Active Fleet</div>
          <div className="kpi-value">{state.trains.length} Trains</div>
        </div>
        <div className="glass-card kpi">
          <div className="kpi-title">Track Health</div>
          <div className="kpi-value">{health}%</div>
        </div>
        <div className={`glass-card kpi ${brokenTracks > 0 ? 'alert' : ''}`}>
          <div className="kpi-title">Network Status</div>
          <div className="kpi-value">{brokenTracks > 0 ? `${brokenTracks} TRACK BROKEN` : 'NOMINAL'}</div>
        </div>
      </div>

      <div className="glass-card map-container">
        <svg width="100%" height="100%" viewBox="-10 100 920 160">
          {/* Draw Edges */}
          {state.network.edges.map((edge, idx) => {
            const posU = stationPos[edge.u];
            const posV = stationPos[edge.v];
            if (!posU || !posV) return null;
            const hasBroken = Object.values(edge.tracks).some(st => st === 'broken');
            return (
              <line 
                key={idx} 
                x1={posU.x} y1={posU.y} x2={posV.x} y2={posV.y} 
                stroke={hasBroken ? "#ef4444" : "#334155"} 
                strokeWidth={hasBroken ? "5" : "4"} 
                strokeDasharray={hasBroken ? "6 3" : "none"}
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
                <circle cx={hx} cy={hy} r="14" fill="rgba(239, 68, 68, 0.3)" className="pulse" />
                <circle cx={hx} cy={hy} r="8" fill="#EF4444" />
                <text x={hx} y={hy+3} fill="#FFFFFF" fontSize="9" textAnchor="middle" fontWeight="bold">✕</text>
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
          <div className="panel-header">
            <h3>AI Multi-Agent Reasoning Brain</h3>
            <span className={`ai-status-badge ${aiDebating || state.emergencies.length > 0 ? 'active' : ''}`}>
              {aiDebating || state.emergencies.length > 0 ? '⚡ DEBATING RESOLUTION' : '● ONLINE (2 AGENTS)'}
            </span>
          </div>
          <div className="ai-brain" style={{height: '350px'}}>
            {state.ai_brain.slice().reverse().map((log, i) => {
              let typeClass = '';
              if (log.includes("[DISPATCHER]")) typeClass = 'ai-dispatcher';
              else if (log.includes("[SAFETY INSPECTOR]")) typeClass = 'ai-safety';
              else if (log.includes("[RAG]")) typeClass = 'ai-rag';
              
              return <div key={i} className={`ai-entry ${typeClass}`}>{log}</div>;
            })}
            {state.ai_brain.length === 0 && (
              <div style={{color: '#64748B', fontStyle: 'italic', padding: '1rem'}}>
                Multi-Agent system standing by (Dispatcher AI + Safety Inspector RAG ready)...
              </div>
            )}
          </div>
        </div>

        {/* Column 2: Live Section Status */}
        <div className="glass-card">
          <div className="panel-header">
            <h3>Live Section Status</h3>
            <span className="section-count-badge">{sections.length} Sectors</span>
          </div>
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
              );
            })}
          </div>
        </div>

        {/* Column 3: Hazard Injection & Logs */}
        <div style={{display: 'flex', flexDirection: 'column', gap: '1.5rem'}}>
          <div className="glass-card hazard-panel" style={{marginTop: 0}}>
            <h3 style={{marginBottom: '0.75rem', color: '#EF4444'}}>Inject Track Failure</h3>
            <p style={{fontSize: '0.75rem', color: '#94A3B8', marginBottom: '0.75rem'}}>
              Simulate physical rail breakdown to test Multi-Agent AI debate & rerouting.
            </p>
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
            
            <button 
              className="btn btn-danger" 
              style={{width: '100%', justifyContent: 'center', display: 'flex', alignItems: 'center', gap: '0.5rem'}} 
              onClick={injectHazard} 
              disabled={!selectedTrack || isInjecting}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
              {isInjecting ? "🚨 Injecting & Invoking AI..." : "Break Track"}
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
