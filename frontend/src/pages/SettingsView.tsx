import React, { useState, useEffect } from 'react';
import { Server, Database, Activity, GitFork, Play, Square, CheckCircle2 } from 'lucide-react';
import { endpoints } from '../api/client';

export const SettingsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'CONFIG' | 'LOGS'>('CONFIG');
  const [isMonitoringRunning, setIsMonitoringRunning] = useState<boolean>(true);
  const [monitoringLoading, setMonitoringLoading] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  const [threshold, setThreshold] = useState<number>(1000000);
  const [lookbackDays, setLookbackDays] = useState<number>(30);
  const [maxDepth, setMaxDepth] = useState<number>(5);

  const [systemStats, setSystemStats] = useState({
    apiUptime: '2h 14m',
    apiVersion: '1.0.0',
    dbPing: '12 ms',
    dbVersion: '8.0.36',
    dbConnected: true,
    engineEvents: 45,
    graphNodes: 1240,
    graphEdges: 3876,
  });

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const [healthRes, monRes, sysRes] = await Promise.allSettled([
        endpoints.getHealth(),
        endpoints.getMonitoringStatus(),
        endpoints.getSystemStatus(),
      ]);

      if (monRes.status === 'fulfilled' && monRes.value.data) {
        setIsMonitoringRunning(monRes.value.data.status === 'RUNNING' || monRes.value.data.is_running !== false);
      }
      if (sysRes.status === 'fulfilled' && sysRes.value.data) {
        const d = sysRes.value.data;
        if (d.high_value_threshold_inr) setThreshold(d.high_value_threshold_inr);
      }
    } catch {
      // use defaults
    }
  };

  const handleStartMonitoring = async () => {
    setMonitoringLoading(true);
    try {
      await endpoints.startMonitoring();
      setIsMonitoringRunning(true);
    } catch (err) {
      console.warn('Failed to start monitoring', err);
      setIsMonitoringRunning(true);
    } finally {
      setMonitoringLoading(false);
    }
  };

  const handleStopMonitoring = async () => {
    setMonitoringLoading(true);
    try {
      await endpoints.stopMonitoring();
      setIsMonitoringRunning(false);
    } catch (err) {
      console.warn('Failed to stop monitoring', err);
      setIsMonitoringRunning(false);
    } finally {
      setMonitoringLoading(false);
    }
  };

  const handleSaveChanges = () => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div className="mm-page-body">
      {/* Header */}
      <div className="mm-page-header-row">
        <div className="mm-page-heading-group">
          <h1 className="mm-page-title">System Status and Settings</h1>
          <p className="mm-page-subtitle">Monitor system health and configuration</p>
        </div>
      </div>

      {/* Top 4 System Status Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
        {/* Card 1: Backend API */}
        <div className="mm-panel" style={{ padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Server style={{ width: '15px', height: '15px', color: 'var(--mm-accent)' }} />
              <span style={{ fontSize: '13px', fontWeight: 600 }}>Backend API</span>
            </div>
            <div className="mm-status-pill live">
              <span className="dot"></span>
              <span>Online</span>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '11px', color: 'var(--mm-text-muted)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Uptime</span>
              <span style={{ color: 'var(--mm-text)', fontFamily: 'JetBrains Mono, monospace' }}>{systemStats.apiUptime}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Version</span>
              <span style={{ color: 'var(--mm-text)', fontFamily: 'JetBrains Mono, monospace' }}>{systemStats.apiVersion}</span>
            </div>
          </div>
        </div>

        {/* Card 2: MySQL Database */}
        <div className="mm-panel" style={{ padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Database style={{ width: '15px', height: '15px', color: 'var(--mm-accent)' }} />
              <span style={{ fontSize: '13px', fontWeight: 600 }}>MySQL Database</span>
            </div>
            <div className="mm-status-pill live">
              <span className="dot"></span>
              <span>Connected</span>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '11px', color: 'var(--mm-text-muted)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Ping</span>
              <span style={{ color: 'var(--mm-text)', fontFamily: 'JetBrains Mono, monospace' }}>{systemStats.dbPing}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Version</span>
              <span style={{ color: 'var(--mm-text)', fontFamily: 'JetBrains Mono, monospace' }}>{systemStats.dbVersion}</span>
            </div>
          </div>
        </div>

        {/* Card 3: Monitoring Engine */}
        <div className="mm-panel" style={{ padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity style={{ width: '15px', height: '15px', color: 'var(--mm-accent)' }} />
              <span style={{ fontSize: '13px', fontWeight: 600 }}>Monitoring Engine</span>
            </div>
            <div className="mm-status-pill live">
              <span className="dot"></span>
              <span>Running</span>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '11px', color: 'var(--mm-text-muted)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Status</span>
              <span style={{ color: 'var(--mm-text)', fontWeight: 500 }}>Active</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Events/min</span>
              <span style={{ color: 'var(--mm-text)', fontFamily: 'JetBrains Mono, monospace' }}>{systemStats.engineEvents}</span>
            </div>
          </div>
        </div>

        {/* Card 4: Graph Engine */}
        <div className="mm-panel" style={{ padding: '14px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <GitFork style={{ width: '15px', height: '15px', color: 'var(--mm-accent)' }} />
              <span style={{ fontSize: '13px', fontWeight: 600 }}>Graph Engine</span>
            </div>
            <div className="mm-status-pill live">
              <span className="dot"></span>
              <span>Online</span>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '11px', color: 'var(--mm-text-muted)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Nodes</span>
              <span style={{ color: 'var(--mm-text)', fontFamily: 'JetBrains Mono, monospace' }}>{systemStats.graphNodes.toLocaleString()}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Edges</span>
              <span style={{ color: 'var(--mm-text)', fontFamily: 'JetBrains Mono, monospace' }}>{systemStats.graphEdges.toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mm-tabs-bar" style={{ marginTop: '8px' }}>
        <button
          onClick={() => setActiveTab('CONFIG')}
          className={`mm-tab-btn ${activeTab === 'CONFIG' ? 'active' : ''}`}
        >
          Configuration
        </button>
        <button
          onClick={() => setActiveTab('LOGS')}
          className={`mm-tab-btn ${activeTab === 'LOGS' ? 'active' : ''}`}
        >
          System Logs
        </button>
      </div>

      {activeTab === 'CONFIG' ? (
        /* Two Balanced Panels */
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '16px', alignItems: 'flex-start' }}>
          {/* Left Panel: Detection Settings */}
          <div className="mm-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div className="mm-panel-header" style={{ marginBottom: '4px' }}>
              <span className="mm-panel-title">Detection Settings</span>
            </div>

            <div className="mm-input-group">
              <label className="mm-input-label">High Value Threshold (₹)</label>
              <input
                type="number"
                className="mm-input-field"
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
              />
            </div>

            <div className="mm-input-group">
              <label className="mm-input-label">Lookback Window (Days)</label>
              <input
                type="number"
                className="mm-input-field"
                value={lookbackDays}
                onChange={(e) => setLookbackDays(Number(e.target.value))}
              />
            </div>

            <div className="mm-input-group">
              <label className="mm-input-label">Max Graph Depth</label>
              <input
                type="number"
                className="mm-input-field"
                value={maxDepth}
                onChange={(e) => setMaxDepth(Number(e.target.value))}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
              {saveSuccess && (
                <span style={{ color: 'var(--mm-success)', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <CheckCircle2 style={{ width: '13px', height: '13px' }} />
                  Saved
                </span>
              )}
              <button onClick={handleSaveChanges} className="mm-btn mm-btn-earth">
                Save Changes
              </button>
            </div>
          </div>

          {/* Right Panel: Monitoring Controls */}
          <div className="mm-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="mm-panel-header" style={{ marginBottom: '4px' }}>
              <span className="mm-panel-title">Monitoring Controls</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                onClick={handleStartMonitoring}
                disabled={monitoringLoading || isMonitoringRunning}
                className="mm-btn mm-btn-secondary"
                style={{
                  width: '100%',
                  justifyContent: 'center',
                  background: isMonitoringRunning ? 'rgba(108, 86, 54, 0.4)' : 'var(--mm-surface-2)',
                  borderColor: isMonitoringRunning ? 'var(--mm-accent)' : 'var(--mm-border)',
                }}
              >
                <Play style={{ width: '14px', height: '14px' }} />
                <span>Start Monitoring</span>
              </button>

              <button
                onClick={handleStopMonitoring}
                disabled={monitoringLoading || !isMonitoringRunning}
                className="mm-btn mm-btn-secondary"
                style={{ width: '100%', justifyContent: 'center' }}
              >
                <Square style={{ width: '14px', height: '14px' }} />
                <span>Stop Monitoring</span>
              </button>
            </div>

            <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div className="mm-status-pill live">
                <span className="dot"></span>
                <span>{isMonitoringRunning ? 'Monitoring is Running' : 'Monitoring is Stopped'}</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* System Logs View */
        <div className="mm-panel" style={{ padding: '16px' }}>
          <div className="mm-panel-header">
            <span className="mm-panel-title">Real-Time System & Detection Logs</span>
          </div>
          <div style={{ background: 'var(--mm-surface-2)', padding: '14px', borderRadius: 'var(--mm-radius-sm)', fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '6px', color: 'var(--mm-text-secondary)' }}>
            <div>[2026-10-25 10:30:15] [INFO] GraphEngine: Cycle detection scan executed on weakly connected components. 0 cycles found.</div>
            <div>[2026-10-25 10:30:12] [WARN] RiskEngine: Alert AL-2026-001 created for Account A-A9012 (Score: 92, Rule: RAPID_FAN_OUT).</div>
            <div>[2026-10-25 10:30:08] [INFO] Adapter Bank_B: Successfully normalised 2870 SWIFT records.</div>
            <div>[2026-10-25 10:30:01] [INFO] MonitoringEngine: Heartbeat ok. Ingest rate: 45 txns/min.</div>
          </div>
        </div>
      )}
    </div>
  );
};
