import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { NetworkGraph, GraphEntityNode, GraphEntityEdge } from '../components/NetworkGraph';
import { endpoints } from '../api/client';
import { Search, ChevronDown, CheckCircle, ShieldAlert, Plus, Layers } from 'lucide-react';

const DEFAULT_NODES: GraphEntityNode[] = [
  { id: 'Victim', label: 'Victim\nV-V001', isVictim: true, riskScore: 10 },
  { id: 'A-A9012', label: 'A-A9012', isSuspicious: true, bankCode: 'BANK_A', riskScore: 85 },
  { id: 'B-B1003', label: 'B-B1003', isSuspicious: true, bankCode: 'BANK_B', riskScore: 92 },
  { id: 'C-C7782', label: 'C-C7782', isSuspicious: true, bankCode: 'BANK_C', riskScore: 78 },
  { id: 'D-D4421', label: 'D-D4421', isSuspicious: true, bankCode: 'BANK_D', riskScore: 96 },
];

const DEFAULT_EDGES: GraphEntityEdge[] = [
  { id: 'e1', source: 'Victim', target: 'A-A9012', amount: 400000, label: '₹4,00,000', isSuspicious: true, timestamp: '2026-10-25' },
  { id: 'e2', source: 'A-A9012', target: 'B-B1003', amount: 200000, label: '₹2,00,000', isSuspicious: true, timestamp: '2026-10-26' },
  { id: 'e3', source: 'A-A9012', target: 'C-C7782', amount: 200000, label: '₹2,00,000', isSuspicious: true, timestamp: '2026-10-26' },
  { id: 'e4', source: 'B-B1003', target: 'D-D4421', amount: 200000, label: '₹2,00,000', isSuspicious: true, timestamp: '2026-10-23' },
  { id: 'e5', source: 'C-C7782', target: 'D-D4421', amount: 200000, label: '₹2,00,000', isSuspicious: true, timestamp: '2026-10-23' },
];

export const InvestigationView: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [investigationId, setInvestigationId] = useState<string>('INV-2026-003');
  const [selectedEntityId, setSelectedEntityId] = useState<string>('B-B1003');
  const [selectedEntity, setSelectedEntity] = useState<any>({
    type: 'account',
    account: 'B-B1003',
    bank: 'National Fin Bank',
    accountType: 'Savings',
    balance: '₹2,15,430',
    totalIn: '₹8,50,000',
    totalOut: '₹7,20,000',
    dwellTime: '5 mins',
    passThrough: '98%',
    counterparties: 4,
    riskIndicators: [
      'High pass-through ratio',
      'Short dwell time',
      'Unusual counterparty (D-D4421)',
      'Historical transfer before victim TX',
    ],
  });

  const [notes, setNotes] = useState<string[]>([]);
  const [status, setStatus] = useState<string>('In Progress');

  useEffect(() => {
    loadInvestigationData();
  }, [investigationId]);

  const loadInvestigationData = async () => {
    try {
      const res = await endpoints.getInvestigationGraph(investigationId);
      if (res.data?.graph?.elements) {
        // We can parse API graph if present, or maintain canonical Scenario 3 view
      }
    } catch {
      // canonical view active
    }
  };

  const handleNodeSelect = (node: GraphEntityNode | null) => {
    if (!node) return;
    setSelectedEntityId(node.id);
    if (node.id === 'B-B1003') {
      setSelectedEntity({
        type: 'account',
        account: 'B-B1003',
        bank: 'National Fin Bank',
        accountType: 'Savings',
        balance: '₹2,15,430',
        totalIn: '₹8,50,000',
        totalOut: '₹7,20,000',
        dwellTime: '5 mins',
        passThrough: '98%',
        counterparties: 4,
        riskIndicators: [
          'High pass-through ratio',
          'Short dwell time',
          'Unusual counterparty (D-D4421)',
          'Historical transfer before victim TX',
        ],
      });
    } else if (node.id === 'A-A9012') {
      setSelectedEntity({
        type: 'account',
        account: 'A-A9012',
        bank: 'Metropolitan Bank',
        accountType: 'Current',
        balance: '₹12,500',
        totalIn: '₹4,00,000',
        totalOut: '₹4,00,000',
        dwellTime: '12 mins',
        passThrough: '100%',
        counterparties: 3,
        riskIndicators: [
          'Immediate rapid turnover',
          'Exact amount conservation split',
          'Zero standing balance',
        ],
      });
    } else if (node.id === 'D-D4421') {
      setSelectedEntity({
        type: 'account',
        account: 'D-D4421',
        bank: 'Continental Bank',
        accountType: 'Corporate Escrow',
        balance: '₹14,80,000',
        totalIn: '₹4,00,000',
        totalOut: '₹20,000',
        dwellTime: 'N/A (Sink)',
        passThrough: '5%',
        counterparties: 6,
        riskIndicators: [
          'Aggregated funnel endpoint',
          'Multiple incoming pre-positioned links',
          'High risk score (96/100)',
        ],
      });
    } else {
      setSelectedEntity({
        type: 'account',
        account: node.id,
        bank: node.bankCode || 'Metropolitan Bank',
        accountType: 'Savings',
        balance: '₹1,50,000',
        totalIn: '₹4,00,000',
        totalOut: '₹2,00,000',
        dwellTime: '15 mins',
        passThrough: '50%',
        counterparties: 2,
        riskIndicators: ['Under active forensic review'],
      });
    }
  };

  const handleEdgeSelect = (edge: GraphEntityEdge | null) => {
    if (!edge) return;
    setSelectedEntityId(edge.id);
    setSelectedEntity({
      type: 'transaction',
      txId: edge.id,
      from: edge.source,
      to: edge.target,
      amount: `₹${edge.amount.toLocaleString()}`,
      timestamp: edge.timestamp || '2026-10-25 10:30',
      status: 'Settled',
      riskIndicators: [
        'Flagged by Graph Analytics Engine',
        edge.source === 'Victim' ? 'Reported Initial Fraud Victim Transfer' : 'Rapid Intermediary Layering Hop',
      ],
    });
  };

  return (
    <div className="mm-page-body">
      {/* Header */}
      <div className="mm-page-header-row">
        <div className="mm-page-heading-group">
          <h1 className="mm-page-title">Investigation Workspace</h1>
          <p className="mm-page-subtitle">Explore transaction networks, trace funds and analyse evidence</p>
        </div>

        {/* Header Selectors matching reference */}
        <div className="mm-header-controls">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 10px',
              background: 'var(--mm-surface-2)',
              border: '1px solid var(--mm-border)',
              borderRadius: 'var(--mm-radius-sm)',
              fontSize: '11px',
            }}
          >
            <span style={{ color: 'var(--mm-text-muted)' }}>Investigation ID:</span>
            <span style={{ fontWeight: 600, color: 'var(--mm-text)', fontFamily: 'JetBrains Mono, monospace' }}>
              {investigationId}
            </span>
            <ChevronDown style={{ width: '12px', height: '12px', color: 'var(--mm-text-muted)' }} />
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 10px',
              background: 'var(--mm-surface-2)',
              border: '1px solid var(--mm-border)',
              borderRadius: 'var(--mm-radius-sm)',
              fontSize: '11px',
              color: 'var(--mm-text-secondary)',
            }}
          >
            <Search style={{ width: '12px', height: '12px', color: 'var(--mm-accent)' }} />
            <span>Scenario 3</span>
          </div>
        </div>
      </div>

      {/* 3-Column Desktop Grid Layout */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '220px 1fr 250px',
          gap: '16px',
          alignItems: 'stretch',
          minHeight: '520px',
        }}
      >
        {/* Left Column: Investigation Details */}
        <div className="mm-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--mm-text)' }}>
              Investigation Details
            </div>
            <div style={{ marginTop: '8px' }}>
              <span className="mm-badge mm-badge-status-progress">{status}</span>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '11.5px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Entry Type</span>
              <span style={{ color: 'var(--mm-text)', fontWeight: 500 }}>Automatic</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Starting TX</span>
              <span style={{ color: 'var(--mm-text)', fontFamily: 'JetBrains Mono, monospace' }}>TXN1025</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Starting Account</span>
              <span style={{ color: 'var(--mm-text)', fontFamily: 'JetBrains Mono, monospace' }}>A-A9012</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Created At</span>
              <span style={{ color: 'var(--mm-text)', fontSize: '10.5px' }}>2026-10-25 10:30</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Risk Score</span>
              <span style={{ color: 'var(--mm-danger)', fontWeight: 700 }}>82 (High)</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '7px' }}>
            <div style={{ fontSize: '11px', color: 'var(--mm-text-muted)', fontWeight: 600, textTransform: 'uppercase', marginBottom: '2px' }}>
              Actions
            </div>
            <button
              onClick={() => {}}
              className="mm-btn mm-btn-earth"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              Expand Graph
            </button>
            <button
              onClick={() => {}}
              className="mm-btn mm-btn-secondary"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              View Timeline
            </button>
            <button
              onClick={() => {
                const note = prompt('Enter investigation note:');
                if (note) setNotes([...notes, note]);
              }}
              className="mm-btn mm-btn-secondary"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              Add Note
            </button>
            <button
              onClick={() => setStatus('Closed')}
              className="mm-btn mm-btn-secondary"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              Mark as Closed
            </button>
          </div>
        </div>

        {/* Center Column: Cytoscape Graph & Timeline */}
        <div className="mm-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Top Legend */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: '16px', fontSize: '11px', color: 'var(--mm-text-muted)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '9px', height: '9px', borderRadius: '50%', border: '1.5px solid var(--mm-text-secondary)', background: 'transparent' }}></span>
              <span>Account</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ color: 'var(--mm-text-muted)', fontSize: '12px' }}>→</span>
              <span>Transaction</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '9px', height: '9px', borderRadius: '50%', background: 'var(--mm-danger)', border: '1.5px solid var(--mm-danger)' }}></span>
              <span>Suspicious</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: '9px', height: '9px', borderRadius: '50%', border: '2px solid var(--mm-burnt-amber)', background: 'rgba(185, 157, 115, 0.3)' }}></span>
              <span>Selected</span>
            </div>
          </div>

          {/* Interactive Graph Canvas */}
          <div style={{ flex: 1, minHeight: '340px', background: 'var(--mm-surface-2)', border: '1px solid var(--mm-border)', borderRadius: 'var(--mm-radius-sm)', position: 'relative' }}>
            <NetworkGraph
              nodes={DEFAULT_NODES}
              edges={DEFAULT_EDGES}
              selectedId={selectedEntityId}
              onSelectNode={handleNodeSelect}
              onSelectEdge={handleEdgeSelect}
            />
          </div>

          {/* Lower Timeline Container */}
          <div style={{ borderTop: '1px solid var(--mm-border)', paddingTop: '12px' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--mm-text-secondary)', marginBottom: '8px' }}>
              Transaction Timeline
            </div>
            <div style={{ display: 'flex', alignItems: 'stretch', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
              <div style={{ flex: 1, minWidth: '100px', background: 'var(--mm-surface-2)', border: '1px solid var(--mm-border)', borderRadius: 'var(--mm-radius-sm)', padding: '7px 9px', fontSize: '10.5px' }}>
                <div style={{ color: 'var(--mm-text-muted)', fontWeight: 600 }}>Day 0</div>
                <div style={{ fontWeight: 600, color: 'var(--mm-text)', marginTop: '2px' }}>B → D</div>
                <div style={{ color: 'var(--mm-accent)', fontFamily: 'JetBrains Mono, monospace', marginTop: '1px' }}>₹2,00,000</div>
                <div style={{ color: 'var(--mm-text-muted)', fontSize: '9.5px', marginTop: '2px' }}>2026-10-23</div>
              </div>

              <div style={{ flex: 1, minWidth: '100px', background: 'var(--mm-surface-2)', border: '1px solid var(--mm-border)', borderRadius: 'var(--mm-radius-sm)', padding: '7px 9px', fontSize: '10.5px' }}>
                <div style={{ color: 'var(--mm-text-muted)', fontWeight: 600 }}>Day 0</div>
                <div style={{ fontWeight: 600, color: 'var(--mm-text)', marginTop: '2px' }}>C → D</div>
                <div style={{ color: 'var(--mm-accent)', fontFamily: 'JetBrains Mono, monospace', marginTop: '1px' }}>₹2,00,000</div>
                <div style={{ color: 'var(--mm-text-muted)', fontSize: '9.5px', marginTop: '2px' }}>2026-10-23</div>
              </div>

              <div style={{ flex: 1, minWidth: '110px', background: 'rgba(184, 92, 80, 0.1)', border: '1px solid rgba(184, 92, 80, 0.35)', borderRadius: 'var(--mm-radius-sm)', padding: '7px 9px', fontSize: '10.5px' }}>
                <div style={{ color: 'var(--mm-danger)', fontWeight: 600 }}>Day 2</div>
                <div style={{ fontWeight: 600, color: 'var(--mm-text)', marginTop: '2px' }}>Victim → A</div>
                <div style={{ color: 'var(--mm-danger)', fontFamily: 'JetBrains Mono, monospace', marginTop: '1px' }}>₹4,00,000</div>
                <div style={{ color: 'var(--mm-text-muted)', fontSize: '9.5px', marginTop: '2px' }}>2026-10-25</div>
              </div>

              <div style={{ flex: 1, minWidth: '100px', background: 'var(--mm-surface-2)', border: '1px solid var(--mm-border)', borderRadius: 'var(--mm-radius-sm)', padding: '7px 9px', fontSize: '10.5px' }}>
                <div style={{ color: 'var(--mm-text-muted)', fontWeight: 600 }}>Day 3</div>
                <div style={{ fontWeight: 600, color: 'var(--mm-text)', marginTop: '2px' }}>A → B</div>
                <div style={{ color: 'var(--mm-accent)', fontFamily: 'JetBrains Mono, monospace', marginTop: '1px' }}>₹2,00,000</div>
                <div style={{ color: 'var(--mm-text-muted)', fontSize: '9.5px', marginTop: '2px' }}>2026-10-26</div>
              </div>

              <div style={{ flex: 1, minWidth: '100px', background: 'var(--mm-surface-2)', border: '1px solid var(--mm-border)', borderRadius: 'var(--mm-radius-sm)', padding: '7px 9px', fontSize: '10.5px' }}>
                <div style={{ color: 'var(--mm-text-muted)', fontWeight: 600 }}>Day 3</div>
                <div style={{ fontWeight: 600, color: 'var(--mm-text)', marginTop: '2px' }}>A → C</div>
                <div style={{ color: 'var(--mm-accent)', fontFamily: 'JetBrains Mono, monospace', marginTop: '1px' }}>₹2,00,000</div>
                <div style={{ color: 'var(--mm-text-muted)', fontSize: '9.5px', marginTop: '2px' }}>2026-10-26</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Selected Entity Details */}
        <div className="mm-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--mm-text)' }}>
              {selectedEntity.type === 'transaction' ? 'Transaction Details' : 'Account Details'}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '6px', fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, color: 'var(--mm-text)' }}>
              <span>●</span>
              <span>{selectedEntity.account || selectedEntity.txId}</span>
            </div>
          </div>

          {selectedEntity.type === 'account' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '7px', fontSize: '11.5px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Bank</span>
                <span style={{ color: 'var(--mm-text)' }}>{selectedEntity.bank}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Account Type</span>
                <span>{selectedEntity.accountType}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Current Balance</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>{selectedEntity.balance}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Total In (30d)</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{selectedEntity.totalIn}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Total Out (30d)</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{selectedEntity.totalOut}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Dwell Time</span>
                <span>{selectedEntity.dwellTime}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Pass-Through</span>
                <span style={{ color: 'var(--mm-danger)', fontWeight: 600 }}>{selectedEntity.passThrough}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Counterparties</span>
                <span>{selectedEntity.counterparties}</span>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '7px', fontSize: '11.5px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Amount</span>
                <span style={{ color: 'var(--mm-accent)', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>{selectedEntity.amount}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Timestamp</span>
                <span>{selectedEntity.timestamp}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>From</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{selectedEntity.from}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>To</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{selectedEntity.to}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Status</span>
                <span className="mm-badge mm-badge-status-completed">{selectedEntity.status}</span>
              </div>
            </div>
          )}

          {/* Risk Indicators section */}
          <div style={{ borderTop: '1px solid var(--mm-border)', paddingTop: '10px' }}>
            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--mm-danger)', marginBottom: '6px' }}>
              Risk Indicators
            </div>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '5px', padding: 0 }}>
              {selectedEntity.riskIndicators?.map((r: string, idx: number) => (
                <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', fontSize: '11px', color: 'var(--mm-text-secondary)' }}>
                  <span style={{ color: 'var(--mm-danger)', lineHeight: 1 }}>•</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
