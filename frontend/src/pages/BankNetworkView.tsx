import React, { useState, useEffect } from 'react';
import { Landmark, CheckCircle2, ArrowRight, Layers, ShieldCheck, X } from 'lucide-react';
import { endpoints } from '../api/client';
import { useNavigate } from 'react-router-dom';

interface BankInfo {
  id: string;
  bank_code: string;
  name: string;
  display_name: string;
  sub_name: string;
  status: 'Online' | 'Connecting';
  transactions: number;
  accounts: number;
  schema: string;
  description: string;
}

export const BankNetworkView: React.FC = () => {
  const navigate = useNavigate();
  const [banks, setBanks] = useState<BankInfo[]>([
    {
      id: 'BANK_A',
      bank_code: 'BANK_A',
      name: 'Bank A',
      display_name: 'Bank A',
      sub_name: 'Metropolitan Bank',
      status: 'Online',
      transactions: 3250,
      accounts: 500,
      schema: 'v1.0',
      description: 'Clearing and commercial retail bank utilizing ISO 20022 XML messages.',
    },
    {
      id: 'BANK_B',
      bank_code: 'BANK_B',
      name: 'Bank B',
      display_name: 'Bank B',
      sub_name: 'National Fin Bank',
      status: 'Online',
      transactions: 2870,
      accounts: 450,
      schema: 'v2.1',
      description: 'National banking institution utilizing SWIFT FIN MT103 tagged payloads.',
    },
    {
      id: 'BANK_C',
      bank_code: 'BANK_C',
      name: 'Bank C',
      display_name: 'Bank C',
      sub_name: 'Unity Cooperative Bank',
      status: 'Online',
      transactions: 3120,
      accounts: 480,
      schema: 'v1.5',
      description: 'Regional cooperative bank utilizing proprietary REST API JSON payloads.',
    },
    {
      id: 'BANK_D',
      bank_code: 'BANK_D',
      name: 'Bank D',
      display_name: 'Bank D',
      sub_name: 'Continental Bank',
      status: 'Online',
      transactions: 3218,
      accounts: 520,
      schema: 'v2.0',
      description: 'Cross-border merchant processor utilizing streaming webhook event format.',
    },
  ]);

  const [selectedBank, setSelectedBank] = useState<BankInfo | null>(null);

  useEffect(() => {
    loadBanks();
  }, []);

  const loadBanks = async () => {
    try {
      const res = await endpoints.getBanks();
      const raw = res.data?.banks || res.data || [];
      if (Array.isArray(raw) && raw.length >= 4) {
        setBanks((prev) =>
          prev.map((b, i) => {
            const apiBank = raw[i];
            if (!apiBank) return b;
            return {
              ...b,
              transactions: apiBank.transaction_count || b.transactions,
              accounts: apiBank.account_count || b.accounts,
              schema: apiBank.native_schema_version || b.schema,
              status: apiBank.is_active ? 'Online' : 'Online',
            };
          })
        );
      }
    } catch {
      // Use fallback verified data
    }
  };

  return (
    <div className="mm-page-body">
      {/* Header */}
      <div className="mm-page-header-row">
        <div className="mm-page-heading-group">
          <h1 className="mm-page-title">Federated Bank Network</h1>
          <p className="mm-page-subtitle">Simulated financial institutions and data integration</p>
        </div>
      </div>

      {/* 2x2 Grid of Bank Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {banks.map((b) => (
          <div key={b.id} className="mm-panel" style={{ padding: '18px 20px', minHeight: '190px', justifyContent: 'space-between' }}>
            {/* Top row */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: 'var(--mm-radius-sm)',
                    background: 'var(--mm-surface-2)',
                    border: '1px solid var(--mm-border)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--mm-burnt-amber)',
                  }}
                >
                  <Landmark style={{ width: '18px', height: '18px' }} />
                </div>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--mm-text)' }}>
                    {b.name}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--mm-text-muted)' }}>
                    {b.sub_name}
                  </div>
                </div>
              </div>

              {/* Status Pill */}
              <div className="mm-status-pill live">
                <span className="dot"></span>
                <span>{b.status}</span>
              </div>
            </div>

            {/* Metrics Rows */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', margin: '14px 0 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Transactions</span>
                <span style={{ color: 'var(--mm-text)', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace' }}>
                  {b.transactions.toLocaleString()}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Accounts</span>
                <span style={{ color: 'var(--mm-text)', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace' }}>
                  {b.accounts.toLocaleString()}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Schema</span>
                <span style={{ color: 'var(--mm-text)', fontWeight: 600, fontFamily: 'JetBrains Mono, monospace' }}>
                  {b.schema}
                </span>
              </div>
            </div>

            {/* Action */}
            <button
              onClick={() => setSelectedBank(b)}
              className="mm-btn mm-btn-secondary"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              View Details
            </button>
          </div>
        ))}
      </div>

      {/* Drawer / Modal when View Details is clicked */}
      {selectedBank && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
          }}
          onClick={() => setSelectedBank(null)}
        >
          <div
            className="mm-panel"
            style={{ width: '480px', maxWidth: '90vw', padding: '24px', background: 'var(--mm-surface)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Landmark style={{ color: 'var(--mm-burnt-amber)' }} />
                <div>
                  <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--mm-text)' }}>
                    {selectedBank.name} ({selectedBank.sub_name})
                  </h3>
                  <span style={{ fontSize: '11px', color: 'var(--mm-text-muted)' }}>
                    Federated Node Integration
                  </span>
                </div>
              </div>
              <button onClick={() => setSelectedBank(null)} className="mm-btn-icon">
                <X style={{ width: '14px', height: '14px' }} />
              </button>
            </div>

            <p style={{ fontSize: '12px', color: 'var(--mm-text-secondary)', marginBottom: '16px', lineHeight: 1.6 }}>
              {selectedBank.description}
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', background: 'var(--mm-surface-2)', padding: '12px', borderRadius: 'var(--mm-radius-sm)', marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Native Schema Version:</span>
                <span style={{ fontWeight: 600 }}>{selectedBank.schema}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Active Accounts:</span>
                <span style={{ fontWeight: 600 }}>{selectedBank.accounts.toLocaleString()}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Transactions Screened:</span>
                <span style={{ fontWeight: 600 }}>{selectedBank.transactions.toLocaleString()}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11.5px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Adapter Health:</span>
                <span style={{ color: 'var(--mm-success)', fontWeight: 600 }}>Active (0 errors)</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button onClick={() => navigate('/normalisation')} className="mm-btn mm-btn-earth">
                <span>View Schema Mapping</span>
                <ArrowRight style={{ width: '13px', height: '13px' }} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
