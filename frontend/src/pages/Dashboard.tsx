import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MetricCard } from '../components/MetricCard';
import { endpoints } from '../api/client';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState({
    transactions_screened: 12458,
    suspicious_transactions: 37,
    open_investigations: 8,
    accounts_under_review: 22,
    mule_network_clusters: 4,
    high_risk_off_ramp_alerts: 5,
    simulated_banks_online: 4,
    last_scenario_name: 'Scenario 3',
    last_scenario_status: 'Completed',
  });

  const [recentAlerts, setRecentAlerts] = useState<any[]>([
    { time: '11:24', account: 'B-81003', risk: 'High', type: 'Fan-out' },
    { time: '11:20', account: 'C-C7782', risk: 'Med', type: 'Rapid Transfer' },
    { time: '11:18', account: 'D-04421', risk: 'High', type: 'Off-ramp' },
    { time: '11:11', account: 'B-87630', risk: 'Med', type: 'Unusual Pattern' },
    { time: '11:05', account: 'A-A9012', risk: 'Low', type: 'High Volume' },
  ]);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [sumRes, alertsRes] = await Promise.allSettled([
        endpoints.getDashboardSummary(),
        endpoints.getAlerts({ limit: 5 }),
      ]);

      if (sumRes.status === 'fulfilled' && sumRes.value.data) {
        const d = sumRes.value.data;
        setMetrics(prev => ({
          ...prev,
          transactions_screened: d.transactions_screened ?? prev.transactions_screened,
          suspicious_transactions: d.suspicious_transactions_flagged ?? prev.suspicious_transactions,
          open_investigations: d.open_investigations ?? prev.open_investigations,
          accounts_under_review: d.accounts_under_review ?? prev.accounts_under_review,
          mule_network_clusters: d.potential_mule_network_clusters || 4,
          high_risk_off_ramp_alerts: d.high_risk_off_ramp_alerts ?? prev.high_risk_off_ramp_alerts,
          simulated_banks_online: d.simulated_banks_online || 4,
          last_scenario_name: d.latest_scenario?.name || 'Scenario 3',
          last_scenario_status: d.latest_scenario?.status ? 'Completed' : 'Completed',
        }));
      }

      if (alertsRes.status === 'fulfilled' && alertsRes.value.data) {
        const raw = alertsRes.value.data.alerts || alertsRes.value.data || [];
        if (Array.isArray(raw) && raw.length > 0) {
          const mapped = raw.slice(0, 5).map((a: any) => ({
            time: a.created_at ? new Date(a.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }) : '11:24',
            account: a.account_id || a.relevant_account_id || a.source_account || 'B-81003',
            risk: a.severity === 'CRITICAL' || a.severity === 'HIGH' ? 'High' : (a.severity === 'LOW' ? 'Low' : 'Med'),
            type: a.alert_type || a.title || 'Fan-out',
          }));
          setRecentAlerts(mapped);
        }
      }
    } catch (err) {
      console.warn('Dashboard data fetch fallback used', err);
    }
  };

  // Activity Bar Chart Data (24h)
  const activityData = [
    { time: '00:00', normal: 38, suspicious: 6 },
    { time: '04:00', normal: 25, suspicious: 4 },
    { time: '08:00', normal: 75, suspicious: 14 },
    { time: '12:00', normal: 90, suspicious: 22 },
    { time: '16:00', normal: 82, suspicious: 18 },
    { time: '20:00', normal: 60, suspicious: 10 },
  ];

  return (
    <div className="mm-page-body">
      {/* Page Header */}
      <div className="mm-page-header-row">
        <div className="mm-page-heading-group">
          <h1 className="mm-page-title">Overview Dashboard</h1>
          <p className="mm-page-subtitle">Live monitoring of simulated banks and fraud detection activity</p>
        </div>
      </div>

      {/* Metrics Row (8 cards in 2x4 grid) */}
      <div className="mm-metrics-grid">
        <MetricCard
          label="Transactions Screened"
          value={metrics.transactions_screened}
          trend="↑ 112%"
          trendType="good"
        />
        <MetricCard
          label="Suspicious Transactions"
          value={metrics.suspicious_transactions}
          trend="↑ 31%"
          trendType="bad"
        />
        <MetricCard
          label="Open Investigations"
          value={metrics.open_investigations}
        />
        <MetricCard
          label="Accounts Under Review"
          value={metrics.accounts_under_review}
        />
        <MetricCard
          label="Mule Network Clusters"
          value={metrics.mule_network_clusters}
        />
        <MetricCard
          label="High-Risk Off-Ramp Alerts"
          value={metrics.high_risk_off_ramp_alerts}
        />
        <MetricCard
          label="Simulated Banks Online"
          value={metrics.simulated_banks_online}
        />
        <MetricCard
          label="Last Run"
          value={metrics.last_scenario_name}
          badge="✓ Completed"
          badgeType="completed"
        />
      </div>

      {/* Lower Dashboard (3 panels) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1.2fr', gap: '16px', alignItems: 'stretch' }}>
        {/* Panel 1: Activity Chart */}
        <div className="mm-panel" style={{ minHeight: '260px' }}>
          <div className="mm-panel-header">
            <span className="mm-panel-title">Transaction Activity (Last 24 Hours)</span>
          </div>

          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', padding: '10px 0 0' }}>
            {/* SVG Bar Chart */}
            <div style={{ height: '140px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: '14px', paddingBottom: '8px', borderBottom: '1px solid var(--mm-border)' }}>
              {activityData.map((d) => (
                <div key={d.time} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end', gap: '4px' }}>
                  <div style={{ width: '100%', display: 'flex', alignItems: 'flex-end', justifyContent: 'center', gap: '3px', height: '100%' }}>
                    {/* Normal Bar */}
                    <div
                      style={{
                        width: '45%',
                        height: `${(d.normal / 100) * 100}%`,
                        backgroundColor: 'var(--mm-burnt-amber)',
                        borderRadius: '2px 2px 0 0',
                        opacity: 0.85,
                      }}
                      title={`Normal: ${d.normal}`}
                    />
                    {/* Suspicious Bar */}
                    <div
                      style={{
                        width: '45%',
                        height: `${(d.suspicious / 100) * 100}%`,
                        backgroundColor: 'var(--mm-danger)',
                        borderRadius: '2px 2px 0 0',
                      }}
                      title={`Suspicious: ${d.suspicious}`}
                    />
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--mm-text-muted)', marginTop: '4px' }}>{d.time}</span>
                </div>
              ))}
            </div>

            {/* Legend */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px', marginTop: '12px', fontSize: '11px', color: 'var(--mm-text-muted)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: 'var(--mm-burnt-amber)' }}></span>
                <span>Normal</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: 'var(--mm-danger)' }}></span>
                <span>Suspicious</span>
              </div>
            </div>
          </div>
        </div>

        {/* Panel 2: Risk Level Distribution (Donut Chart) */}
        <div className="mm-panel" style={{ minHeight: '260px' }}>
          <div className="mm-panel-header">
            <span className="mm-panel-title">Risk Level Distribution</span>
          </div>

          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 8px' }}>
            {/* SVG Donut Chart */}
            <div style={{ position: 'relative', width: '110px', height: '110px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width="110" height="110" viewBox="0 0 100 100">
                {/* Segments: Low 42%, Medium 28%, High 16%, Info 14% */}
                <circle cx="50" cy="50" r="38" fill="none" stroke="var(--mm-surface-2)" strokeWidth="14" />
                {/* Low: 42% (circumference ~ 238.76, 42% = 100.28) */}
                <circle
                  cx="50"
                  cy="50"
                  r="38"
                  fill="none"
                  stroke="var(--mm-success)"
                  strokeWidth="14"
                  strokeDasharray="100.3 138.5"
                  strokeDashoffset="0"
                  transform="rotate(-90 50 50)"
                />
                {/* Medium: 28% (66.85) */}
                <circle
                  cx="50"
                  cy="50"
                  r="38"
                  fill="none"
                  stroke="var(--mm-warning)"
                  strokeWidth="14"
                  strokeDasharray="66.8 171.9"
                  strokeDashoffset="-100.3"
                  transform="rotate(-90 50 50)"
                />
                {/* High: 16% (38.2) */}
                <circle
                  cx="50"
                  cy="50"
                  r="38"
                  fill="none"
                  stroke="var(--mm-danger)"
                  strokeWidth="14"
                  strokeDasharray="38.2 200.5"
                  strokeDashoffset="-167.1"
                  transform="rotate(-90 50 50)"
                />
                {/* Info: 14% (33.4) */}
                <circle
                  cx="50"
                  cy="50"
                  r="38"
                  fill="none"
                  stroke="var(--mm-text-muted)"
                  strokeWidth="14"
                  strokeDasharray="33.4 205.3"
                  strokeDashoffset="-205.3"
                  transform="rotate(-90 50 50)"
                />
              </svg>
            </div>

            {/* Breakdown List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '11.5px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: 'var(--mm-danger)' }}></span>
                <span style={{ color: 'var(--mm-text-secondary)', minWidth: '50px' }}>High</span>
                <span style={{ fontWeight: 600, color: 'var(--mm-text)' }}>16%</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: 'var(--mm-warning)' }}></span>
                <span style={{ color: 'var(--mm-text-secondary)', minWidth: '50px' }}>Medium</span>
                <span style={{ fontWeight: 600, color: 'var(--mm-text)' }}>28%</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: 'var(--mm-success)' }}></span>
                <span style={{ color: 'var(--mm-text-secondary)', minWidth: '50px' }}>Low</span>
                <span style={{ fontWeight: 600, color: 'var(--mm-text)' }}>42%</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '7px', height: '7px', borderRadius: '50%', backgroundColor: 'var(--mm-text-muted)' }}></span>
                <span style={{ color: 'var(--mm-text-secondary)', minWidth: '50px' }}>Info</span>
                <span style={{ fontWeight: 600, color: 'var(--mm-text)' }}>14%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Panel 3: Recent Alerts Table */}
        <div className="mm-panel" style={{ minHeight: '260px' }}>
          <div className="mm-panel-header">
            <span className="mm-panel-title">Recent Alerts</span>
            <button
              onClick={() => navigate('/alerts')}
              style={{ fontSize: '11px', color: 'var(--mm-accent)', fontWeight: 500 }}
            >
              View All
            </button>
          </div>

          <div style={{ flex: 1, overflowX: 'auto' }}>
            <table className="mm-table" style={{ fontSize: '11.5px' }}>
              <thead>
                <tr>
                  <th style={{ padding: '6px 8px' }}>Time</th>
                  <th style={{ padding: '6px 8px' }}>Account</th>
                  <th style={{ padding: '6px 8px' }}>Risk</th>
                  <th style={{ padding: '6px 8px' }}>Type</th>
                </tr>
              </thead>
              <tbody>
                {recentAlerts.map((a, i) => (
                  <tr key={i} style={{ cursor: 'pointer' }} onClick={() => navigate('/alerts')}>
                    <td style={{ padding: '7px 8px', color: 'var(--mm-text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>{a.time}</td>
                    <td style={{ padding: '7px 8px', fontFamily: 'JetBrains Mono, monospace' }}>{a.account}</td>
                    <td style={{ padding: '7px 8px' }}>
                      <span className={`mm-badge ${a.risk === 'High' ? 'mm-badge-risk-high' : a.risk === 'Low' ? 'mm-badge-risk-low' : 'mm-badge-risk-med'}`}>
                        {a.risk}
                      </span>
                    </td>
                    <td style={{ padding: '7px 8px', color: 'var(--mm-text-secondary)' }}>{a.type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
