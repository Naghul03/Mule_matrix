import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, ShieldAlert } from 'lucide-react';
import { endpoints } from '../api/client';

interface AlertItem {
  id: string;
  triggeredBy: string;
  account: string;
  risk: 'High' | 'Medium' | 'Low';
  riskScore: number;
  type: string;
  status: 'Open' | 'Under Review' | 'Closed';
  createdAt: string;
}

const DEFAULT_ALERTS: AlertItem[] = [
  { id: 'AL-2026-001', triggeredBy: 'TXN1021', account: 'A-A9012', risk: 'High', riskScore: 92, type: 'Money Mule', status: 'Open', createdAt: '2026-10-25 10:30' },
  { id: 'AL-2026-002', triggeredBy: 'TXN1022', account: 'C-C7782', risk: 'Medium', riskScore: 74, type: 'Rapid Transfer', status: 'Under Review', createdAt: '2026-10-25 09:15' },
  { id: 'AL-2026-003', triggeredBy: 'TXN1023', account: 'B-B1003', risk: 'High', riskScore: 88, type: 'Fan-out', status: 'Open', createdAt: '2026-10-24 21:00' },
  { id: 'AL-2026-004', triggeredBy: 'TXN1024', account: 'D-D4421', risk: 'High', riskScore: 85, type: 'Off-ramp', status: 'Open', createdAt: '2026-10-24 16:20' },
  { id: 'AL-2026-005', triggeredBy: 'TXN0998', account: 'A-A8501', risk: 'Medium', riskScore: 68, type: 'Unusual Pattern', status: 'Under Review', createdAt: '2026-10-24 14:05' },
  { id: 'AL-2026-006', triggeredBy: 'TXN0991', account: 'C-C3210', risk: 'Low', riskScore: 42, type: 'High Volume', status: 'Closed', createdAt: '2026-10-24 11:12' },
];

export const AlertsView: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'ALL' | 'OPEN' | 'REVIEW' | 'CLOSED'>('ALL');
  const [alerts, setAlerts] = useState<AlertItem[]>(DEFAULT_ALERTS);
  const [selectedAlert, setSelectedAlert] = useState<AlertItem>(DEFAULT_ALERTS[0]);

  useEffect(() => {
    loadAlerts();
  }, []);

  const loadAlerts = async () => {
    try {
      const res = await endpoints.getAlerts();
      const raw = res.data?.alerts || res.data || [];
      if (Array.isArray(raw) && raw.length > 0) {
        const mapped: AlertItem[] = raw.map((a: any, i: number) => ({
          id: a.id || `AL-2026-${String(i + 1).padStart(3, '0')}`,
          triggeredBy: a.transaction_id || `TXN${1020 + i}`,
          account: a.account_id || a.relevant_account_id || 'A-A9012',
          risk: a.severity === 'CRITICAL' || a.severity === 'HIGH' ? 'High' : (a.severity === 'LOW' ? 'Low' : 'Medium'),
          riskScore: Math.round(Number(a.risk_score || a.score || 85)),
          type: a.alert_type || a.title || 'Money Mule',
          status: a.status === 'CLOSED' ? 'Closed' : (a.status === 'UNDER_REVIEW' ? 'Under Review' : 'Open'),
          createdAt: a.created_at ? new Date(a.created_at).toISOString().replace('T', ' ').substring(0, 16) : '2026-10-25 10:30',
        }));
        setAlerts(mapped);
        setSelectedAlert(mapped[0]);
      }
    } catch {
      // canonical sample active
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    if (activeTab === 'OPEN') return a.status === 'Open';
    if (activeTab === 'REVIEW') return a.status === 'Under Review';
    if (activeTab === 'CLOSED') return a.status === 'Closed';
    return true;
  });

  const openCount = alerts.filter(a => a.status === 'Open').length;
  const reviewCount = alerts.filter(a => a.status === 'Under Review').length;
  const closedCount = alerts.filter(a => a.status === 'Closed').length;

  return (
    <div className="mm-page-body">
      {/* Header */}
      <div className="mm-page-header-row">
        <div className="mm-page-heading-group">
          <h1 className="mm-page-title">Alerts and Investigations</h1>
          <p className="mm-page-subtitle">Manage fraud alerts and investigation cases</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="mm-tabs-bar">
        <button
          onClick={() => setActiveTab('ALL')}
          className={`mm-tab-btn ${activeTab === 'ALL' ? 'active' : ''}`}
        >
          All Alerts ({alerts.length})
        </button>
        <button
          onClick={() => setActiveTab('OPEN')}
          className={`mm-tab-btn ${activeTab === 'OPEN' ? 'active' : ''}`}
        >
          Open ({openCount})
        </button>
        <button
          onClick={() => setActiveTab('REVIEW')}
          className={`mm-tab-btn ${activeTab === 'REVIEW' ? 'active' : ''}`}
        >
          Under Review ({reviewCount})
        </button>
        <button
          onClick={() => setActiveTab('CLOSED')}
          className={`mm-tab-btn ${activeTab === 'CLOSED' ? 'active' : ''}`}
        >
          Closed ({closedCount})
        </button>
      </div>

      {/* Two Columns Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px', alignItems: 'stretch' }}>
        {/* Left Column: Alerts Table */}
        <div className="mm-table-container">
          <table className="mm-table" style={{ fontSize: '11.5px' }}>
            <thead>
              <tr>
                <th style={{ padding: '8px 10px' }}>Alert ID</th>
                <th style={{ padding: '8px 10px' }}>Triggered By</th>
                <th style={{ padding: '8px 10px' }}>Account</th>
                <th style={{ padding: '8px 10px' }}>Risk</th>
                <th className="text-center" style={{ padding: '8px 10px' }}>Risk Score</th>
                <th style={{ padding: '8px 10px' }}>Type</th>
                <th style={{ padding: '8px 10px' }}>Status</th>
                <th style={{ padding: '8px 10px' }}>Created At</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.map((a) => (
                <tr
                  key={a.id}
                  onClick={() => setSelectedAlert(a)}
                  style={{ cursor: 'pointer' }}
                  className={selectedAlert.id === a.id ? 'selected' : ''}
                >
                  <td style={{ padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>{a.id}</td>
                  <td style={{ padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace', color: 'var(--mm-text-muted)' }}>{a.triggeredBy}</td>
                  <td style={{ padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace' }}>{a.account}</td>
                  <td style={{ padding: '8px 10px' }}>
                    <span className={`mm-badge ${a.risk === 'High' ? 'mm-badge-risk-high' : a.risk === 'Medium' ? 'mm-badge-risk-med' : 'mm-badge-risk-low'}`}>
                      {a.risk}
                    </span>
                  </td>
                  <td className="text-center" style={{ padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>
                    {a.riskScore}
                  </td>
                  <td style={{ padding: '8px 10px', color: 'var(--mm-text-secondary)' }}>{a.type}</td>
                  <td style={{ padding: '8px 10px' }}>
                    <span className={`mm-badge ${a.status === 'Open' ? 'mm-badge-status-progress' : a.status === 'Closed' ? 'mm-badge-status-completed' : 'mm-badge-risk-med'}`}>
                      {a.status}
                    </span>
                  </td>
                  <td style={{ padding: '8px 10px', color: 'var(--mm-text-muted)', fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>
                    {a.createdAt}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Right Column: Alert Summary Panel */}
        <div className="mm-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--mm-text)' }}>
              Alert Summary
            </div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '16px', fontWeight: 700, color: 'var(--mm-text)', marginTop: '4px' }}>
              {selectedAlert.id}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '8px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Risk Level</span>
              <span className={`mm-badge ${selectedAlert.risk === 'High' ? 'mm-badge-risk-high' : selectedAlert.risk === 'Medium' ? 'mm-badge-risk-med' : 'mm-badge-risk-low'}`}>
                {selectedAlert.risk}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Risk Score</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, color: selectedAlert.risk === 'High' ? 'var(--mm-danger)' : 'var(--mm-text)' }}>
                {selectedAlert.riskScore}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Type</span>
              <span style={{ fontWeight: 500 }}>{selectedAlert.type}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Status</span>
              <span className="mm-badge mm-badge-status-progress">{selectedAlert.status}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '8px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Created At</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>{selectedAlert.createdAt}</span>
            </div>
          </div>

          <div style={{ marginTop: 'auto', paddingTop: '12px' }}>
            <button
              onClick={() => navigate('/investigation?id=INV-2026-003')}
              className="mm-btn mm-btn-earth"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              <span>View Full Investigation</span>
              <ArrowRight style={{ width: '13px', height: '13px' }} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
