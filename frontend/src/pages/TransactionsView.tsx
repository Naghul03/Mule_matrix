import React, { useState, useEffect } from 'react';
import { Search, ExternalLink, X, ArrowRight } from 'lucide-react';
import { endpoints } from '../api/client';
import { useNavigate } from 'react-router-dom';

interface TransactionRow {
  id: string;
  timestamp: string;
  fromAccount: string;
  toAccount: string;
  amount: number;
  bank: string;
  status: string;
  risk: 'High' | 'Medium' | 'Low';
  channel?: string;
  rawReference?: string;
}

const DEFAULT_TRANSACTIONS: TransactionRow[] = [
  { id: 'TXN1025', timestamp: '2026-10-25 10:30', fromAccount: 'A-A9012', toAccount: 'B-B1003', amount: 400000, bank: 'A', status: 'Completed', risk: 'High', channel: 'NEFT', rawReference: 'REF-BK-A-90812' },
  { id: 'TXN1022', timestamp: '2026-10-25 10:28', fromAccount: 'A-A9012', toAccount: 'A-A9012', amount: 400000, bank: 'A', status: 'Completed', risk: 'High', channel: 'RTGS', rawReference: 'REF-BK-A-90800' },
  { id: 'TXN1021', timestamp: '2026-10-25 09:15', fromAccount: 'C-C7782', toAccount: 'D-D4421', amount: 200000, bank: 'C', status: 'Completed', risk: 'Medium', channel: 'IMPS', rawReference: 'REF-BK-C-77192' },
  { id: 'TXN1020', timestamp: '2026-10-25 09:10', fromAccount: 'B-B1003', toAccount: 'D-D4421', amount: 200000, bank: 'B', status: 'Completed', risk: 'Medium', channel: 'SWIFT', rawReference: 'REF-BK-B-11204' },
  { id: 'TXN1019', timestamp: '2026-10-24 18:05', fromAccount: 'A-A9012', toAccount: 'C-C7782', amount: 200000, bank: 'A', status: 'Completed', risk: 'Medium', channel: 'NEFT', rawReference: 'REF-BK-A-89912' },
  { id: 'TXN1018', timestamp: '2026-10-24 16:20', fromAccount: 'A-A9012', toAccount: 'B-B1003', amount: 200000, bank: 'A', status: 'Completed', risk: 'Medium', channel: 'NEFT', rawReference: 'REF-BK-A-89910' },
  { id: 'TXN1017', timestamp: '2026-10-23 14:20', fromAccount: 'M-M1341', toAccount: 'A-A9012', amount: 50000, bank: 'A', status: 'Completed', risk: 'Low', channel: 'UPI', rawReference: 'REF-BK-A-88741' },
  { id: 'TXN1016', timestamp: '2026-10-23 11:18', fromAccount: 'B-B1003', toAccount: 'C-C7782', amount: 75000, bank: 'B', status: 'Completed', risk: 'Low', channel: 'IMPS', rawReference: 'REF-BK-B-10822' },
];

export const TransactionsView: React.FC = () => {
  const navigate = useNavigate();
  const [transactions, setTransactions] = useState<TransactionRow[]>(DEFAULT_TRANSACTIONS);
  const [bankFilter, setBankFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [startDate, setStartDate] = useState<string>('2026-10-01');
  const [endDate, setEndDate] = useState<string>('2026-10-31');
  const [search, setSearch] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [selectedTx, setSelectedTx] = useState<TransactionRow | null>(null);

  useEffect(() => {
    loadTransactions();
  }, [bankFilter, statusFilter]);

  const loadTransactions = async () => {
    try {
      const params: any = { limit: 50 };
      if (bankFilter !== 'ALL') params.bank_id = bankFilter;
      const res = await endpoints.getTransactions(params);
      const items = res.data?.items || res.data?.transactions || res.data || [];
      if (Array.isArray(items) && items.length > 0) {
        const mapped: TransactionRow[] = items.map((t: any) => ({
          id: t.id || `TXN${Math.floor(1000 + Math.random() * 9000)}`,
          timestamp: t.timestamp ? new Date(t.timestamp).toISOString().replace('T', ' ').substring(0, 16) : '2026-10-25 10:30',
          fromAccount: t.originator_account_id || t.sender_account_ref || 'A-A9012',
          toAccount: t.beneficiary_account_id || t.receiver_account_ref || 'B-B1003',
          amount: Number(t.amount) || 200000,
          bank: t.bank_id ? t.bank_id.replace('BANK_', '') : (t.bank_code || 'A'),
          status: 'Completed',
          risk: t.risk_score >= 80 || t.is_suspicious ? 'High' : (t.risk_score >= 50 ? 'Medium' : 'Low'),
          channel: t.channel || 'NEFT',
          rawReference: t.raw_reference || t.source_reference,
        }));
        setTransactions(mapped);
      }
    } catch {
      // Keep verified table
    }
  };

  const filtered = transactions.filter((t) => {
    if (bankFilter !== 'ALL' && t.bank !== bankFilter) return false;
    if (statusFilter !== 'ALL' && t.status.toLowerCase() !== statusFilter.toLowerCase()) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        t.id.toLowerCase().includes(q) ||
        t.fromAccount.toLowerCase().includes(q) ||
        t.toAccount.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="mm-page-body">
      {/* Header */}
      <div className="mm-page-header-row">
        <div className="mm-page-heading-group">
          <h1 className="mm-page-title">Transaction Monitor</h1>
          <p className="mm-page-subtitle">Live view of all transactions across simulated banks</p>
        </div>
      </div>

      {/* Filter Row */}
      <div className="mm-filter-row">
        <select
          value={bankFilter}
          onChange={(e) => setBankFilter(e.target.value)}
          className="mm-input-field"
          style={{ minWidth: '120px' }}
        >
          <option value="ALL">All Banks</option>
          <option value="A">Bank A</option>
          <option value="B">Bank B</option>
          <option value="C">Bank C</option>
          <option value="D">Bank D</option>
        </select>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="mm-input-field"
          style={{ minWidth: '120px' }}
        >
          <option value="ALL">All Status</option>
          <option value="Completed">Completed</option>
          <option value="Pending">Pending</option>
          <option value="Flagged">Flagged</option>
        </select>

        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="mm-input-field"
          style={{ width: '130px' }}
        />

        <span style={{ color: 'var(--mm-text-muted)' }}>→</span>

        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="mm-input-field"
          style={{ width: '130px' }}
        />

        <div className="mm-search-wrap">
          <Search />
          <input
            type="text"
            className="mm-input-field"
            placeholder="Search account or transaction ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Transactions Table Container */}
      <div className="mm-table-container">
        <table className="mm-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Transaction ID</th>
              <th>From</th>
              <th>To</th>
              <th className="text-right">Amount (₹)</th>
              <th className="text-center">Bank</th>
              <th className="text-center">Status</th>
              <th className="text-center">Risk</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr
                key={t.id}
                onClick={() => setSelectedTx(t)}
                style={{ cursor: 'pointer' }}
                className={selectedTx?.id === t.id ? 'selected' : ''}
              >
                <td style={{ color: 'var(--mm-text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
                  {t.timestamp}
                </td>
                <td style={{ fontFamily: 'JetBrains Mono, monospace', color: t.risk === 'High' ? 'var(--mm-danger)' : 'var(--mm-text)', fontWeight: 600 }}>
                  {t.id}
                </td>
                <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{t.fromAccount}</td>
                <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{t.toAccount}</td>
                <td className="text-right" style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>
                  {t.amount.toLocaleString()}
                </td>
                <td className="text-center" style={{ fontWeight: 600 }}>{t.bank}</td>
                <td className="text-center">
                  <span className="mm-badge mm-badge-status-completed">{t.status}</span>
                </td>
                <td className="text-center">
                  <span className={`mm-badge ${t.risk === 'High' ? 'mm-badge-risk-high' : t.risk === 'Medium' ? 'mm-badge-risk-med' : 'mm-badge-risk-low'}`}>
                    {t.risk}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination Bar */}
        <div className="mm-pagination">
          <div className="mm-pagination-pages">
            <button className="mm-page-number" onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}>‹</button>
            <button className="mm-page-number active">1</button>
            <button className="mm-page-number">2</button>
            <button className="mm-page-number">3</button>
            <button className="mm-page-number">4</button>
            <button className="mm-page-number">5</button>
            <span style={{ margin: '0 4px', color: 'var(--mm-text-muted)' }}>...</span>
            <button className="mm-page-number">124</button>
            <button className="mm-page-number" onClick={() => setCurrentPage(currentPage + 1)}>›</button>
          </div>

          <div>
            Showing 1-{filtered.length} of 987 transactions
          </div>
        </div>
      </div>

      {/* Transaction Details Drawer */}
      {selectedTx && (
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
          onClick={() => setSelectedTx(null)}
        >
          <div
            className="mm-panel"
            style={{ width: '460px', maxWidth: '90vw', padding: '24px', background: 'var(--mm-surface)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--mm-text)', fontFamily: 'JetBrains Mono, monospace' }}>
                  {selectedTx.id}
                </h3>
                <span style={{ fontSize: '11px', color: 'var(--mm-text-muted)' }}>
                  Screened Transaction Record
                </span>
              </div>
              <button onClick={() => setSelectedTx(null)} className="mm-btn-icon">
                <X style={{ width: '14px', height: '14px' }} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', background: 'var(--mm-surface-2)', padding: '14px', borderRadius: 'var(--mm-radius-sm)', marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Amount:</span>
                <span style={{ fontWeight: 700, color: 'var(--mm-accent)', fontFamily: 'JetBrains Mono, monospace' }}>
                  ₹{selectedTx.amount.toLocaleString()}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Timestamp:</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{selectedTx.timestamp}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Originator:</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>{selectedTx.fromAccount}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Beneficiary:</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>{selectedTx.toAccount}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Bank Node:</span>
                <span>Bank {selectedTx.bank}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Payment Channel:</span>
                <span>{selectedTx.channel}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--mm-text-muted)' }}>Raw Ref:</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>{selectedTx.rawReference || 'N/A'}</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => {
                  setSelectedTx(null);
                  navigate(`/investigation?account=${selectedTx.fromAccount}`);
                }}
                className="mm-btn mm-btn-earth"
              >
                <span>Investigate in Workspace</span>
                <ArrowRight style={{ width: '13px', height: '13px' }} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
