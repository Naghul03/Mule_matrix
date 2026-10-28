import React, { useState } from 'react';
import { ProvenanceTree, ProvenanceTreeNode } from '../components/ProvenanceTree';

const CBDC_ROOT_NODE: ProvenanceTreeNode = {
  id: 'P-100',
  amount: '₹5,00,000',
  numericAmount: 500000,
  parentId: null,
  originTx: 'TXN1010',
  currentHolder: 'A-A9012',
  remaining: '₹0',
  status: 'Split & Transferred',
  createdAt: '2026-10-24 09:30',
  allocationMethod: 'Cryptographic Mint',
  children: [
    {
      id: 'P-101',
      amount: '₹2,00,000',
      numericAmount: 200000,
      parentId: 'P-100',
      originTx: 'TXN1021',
      currentHolder: 'B-B1003',
      remaining: '₹0',
      status: 'Transferred',
      createdAt: '2026-10-24 10:00',
      allocationMethod: 'Deterministic Split',
      children: [
        {
          id: 'P-101A',
          amount: '₹50,000',
          numericAmount: 50000,
          parentId: 'P-101',
          originTx: 'TXN1024',
          currentHolder: 'D-D4421',
          remaining: '₹50,000',
          status: 'Active Unspent',
          createdAt: '2026-10-24 11:20',
          allocationMethod: 'Deterministic Split',
        },
        {
          id: 'P-101B',
          amount: '₹1,50,000',
          numericAmount: 150000,
          parentId: 'P-101',
          originTx: 'TXN1025',
          currentHolder: 'D-D4421',
          remaining: '₹1,50,000',
          status: 'Active Unspent',
          createdAt: '2026-10-24 11:25',
          allocationMethod: 'Deterministic Split',
        },
      ],
    },
    {
      id: 'P-102',
      amount: '₹3,00,000',
      numericAmount: 300000,
      parentId: 'P-100',
      originTx: 'TXN1022',
      currentHolder: 'C-C7782',
      remaining: '₹3,00,000',
      status: 'Active Unspent',
      createdAt: '2026-10-24 10:15',
      allocationMethod: 'Deterministic Split',
    },
  ],
};

const CONVENTIONAL_ROOT_NODE: ProvenanceTreeNode = {
  id: 'ACC-ATTRIB-01',
  amount: '₹5,00,000',
  numericAmount: 500000,
  parentId: null,
  originTx: 'TXN0980',
  currentHolder: 'Victim Acct',
  remaining: '₹0',
  status: 'Disbursed',
  createdAt: '2026-10-23 14:00',
  allocationMethod: 'FIFO Accounting',
  children: [
    {
      id: 'FIFO-HOP-1',
      amount: '₹2,50,000',
      numericAmount: 250000,
      parentId: 'ACC-ATTRIB-01',
      originTx: 'TXN0985',
      currentHolder: 'Intermediary B',
      remaining: '₹0',
      status: 'Forwarded',
      createdAt: '2026-10-23 15:30',
      allocationMethod: 'FIFO Matching',
      children: [
        {
          id: 'FIFO-OUT-1A',
          amount: '₹1,25,000',
          numericAmount: 125000,
          parentId: 'FIFO-HOP-1',
          originTx: 'TXN0992',
          currentHolder: 'Sink Account',
          remaining: '₹1,25,000',
          status: 'Settled',
          createdAt: '2026-10-23 16:45',
          allocationMethod: 'FIFO Matching',
        },
        {
          id: 'FIFO-OUT-1B',
          amount: '₹1,25,000',
          numericAmount: 125000,
          parentId: 'FIFO-HOP-1',
          originTx: 'TXN0993',
          currentHolder: 'ATM Cashout',
          remaining: '₹1,25,000',
          status: 'Settled',
          createdAt: '2026-10-23 17:10',
          allocationMethod: 'FIFO Matching',
        },
      ],
    },
    {
      id: 'FIFO-HOP-2',
      amount: '₹2,50,000',
      numericAmount: 250000,
      parentId: 'ACC-ATTRIB-01',
      originTx: 'TXN0986',
      currentHolder: 'Intermediary C',
      remaining: '₹2,50,000',
      status: 'Retained',
      createdAt: '2026-10-23 15:35',
      allocationMethod: 'FIFO Matching',
    },
  ],
};

export const ProvenanceExplorer: React.FC = () => {
  const [mode, setMode] = useState<'CBDC' | 'CONVENTIONAL'>('CBDC');
  const [selectedNode, setSelectedNode] = useState<ProvenanceTreeNode>(
    CBDC_ROOT_NODE.children![0] // P-101 by default matching reference
  );

  const activeRoot = mode === 'CBDC' ? CBDC_ROOT_NODE : CONVENTIONAL_ROOT_NODE;

  const handleModeChange = (newMode: 'CBDC' | 'CONVENTIONAL') => {
    setMode(newMode);
    const root = newMode === 'CBDC' ? CBDC_ROOT_NODE : CONVENTIONAL_ROOT_NODE;
    setSelectedNode(root.children ? root.children[0] : root);
  };

  return (
    <div className="mm-page-body">
      {/* Header */}
      <div className="mm-page-header-row">
        <div className="mm-page-heading-group">
          <h1 className="mm-page-title">Provenance Explorer</h1>
          <p className="mm-page-subtitle">Track value lineage and attribution through transactions</p>
        </div>
      </div>

      {/* Mode Selector Tabs */}
      <div className="mm-tabs-bar">
        <button
          onClick={() => handleModeChange('CONVENTIONAL')}
          className={`mm-tab-btn ${mode === 'CONVENTIONAL' ? 'active' : ''}`}
        >
          Conventional Attribution
        </button>
        <button
          onClick={() => handleModeChange('CBDC')}
          className={`mm-tab-btn ${mode === 'CBDC' ? 'active' : ''}`}
        >
          CBDC Token Lineage
        </button>
      </div>

      {/* Two Columns Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '16px', alignItems: 'stretch' }}>
        {/* Left Column: Lineage Graph */}
        <div className="mm-panel" style={{ minHeight: '440px', padding: '20px', display: 'flex', flexDirection: 'column' }}>
          <div className="mm-panel-header" style={{ marginBottom: '8px' }}>
            <span className="mm-panel-title">
              {mode === 'CBDC' ? 'Deterministic CBDC Token Tree' : 'Conventional FIFO Attribution Flow'}
            </span>
          </div>

          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ProvenanceTree
              rootNode={activeRoot}
              selectedId={selectedNode.id}
              onSelectNode={(node) => setSelectedNode(node)}
              mode={mode}
            />
          </div>
        </div>

        {/* Right Column: Provenance Details Panel */}
        <div className="mm-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="mm-panel-header" style={{ marginBottom: '0' }}>
            <span className="mm-panel-title">Provenance Details</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Provenance ID</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 600, color: 'var(--mm-accent)' }}>
                {selectedNode.id}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Parent ID</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                {selectedNode.parentId || 'None (Root Token)'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Origin TX</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                {selectedNode.originTx}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Amount</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, color: 'var(--mm-text)' }}>
                {selectedNode.amount}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Current Holder</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 500 }}>
                {selectedNode.currentHolder}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Remaining</span>
              <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                {selectedNode.remaining}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Status</span>
              <span className="mm-badge mm-badge-status-completed">
                {selectedNode.status}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Mode</span>
              <span style={{ color: 'var(--mm-text)' }}>
                {mode === 'CBDC' ? 'Simulated CBDC' : 'Conventional FIFO'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid var(--mm-surface-2)' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Allocation Method</span>
              <span style={{ color: 'var(--mm-text)' }}>
                {selectedNode.allocationMethod}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--mm-text-muted)' }}>Created At</span>
              <span style={{ color: 'var(--mm-text-secondary)', fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' }}>
                {selectedNode.createdAt}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
