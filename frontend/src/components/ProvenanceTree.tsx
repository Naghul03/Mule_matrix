import React from 'react';

export interface ProvenanceTreeNode {
  id: string;
  amount: string;
  numericAmount: number;
  parentId?: string | null;
  originTx: string;
  currentHolder: string;
  remaining: string;
  status: string;
  createdAt: string;
  allocationMethod: string;
  children?: ProvenanceTreeNode[];
}

interface ProvenanceTreeProps {
  rootNode: ProvenanceTreeNode;
  selectedId: string;
  onSelectNode: (node: ProvenanceTreeNode) => void;
  mode: 'CBDC' | 'CONVENTIONAL';
}

export const ProvenanceTree: React.FC<ProvenanceTreeProps> = ({
  rootNode,
  selectedId,
  onSelectNode,
  mode,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%', padding: '20px 0' }}>
      <div style={{ fontSize: '11px', color: 'var(--mm-text-muted)', marginBottom: '14px', fontFamily: 'JetBrains Mono, monospace' }}>
        Provenance ID: {rootNode.id}
      </div>

      {/* Level 0: Root Node */}
      <div
        onClick={() => onSelectNode(rootNode)}
        className={`mm-panel ${selectedId === rootNode.id ? 'selected' : ''}`}
        style={{
          width: '160px',
          padding: '10px 14px',
          textAlign: 'center',
          cursor: 'pointer',
          borderColor: selectedId === rootNode.id ? 'var(--mm-burnt-amber)' : 'var(--mm-border)',
          background: selectedId === rootNode.id ? 'rgba(185, 157, 115, 0.12)' : 'var(--mm-surface-2)',
        }}
      >
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, color: 'var(--mm-text)' }}>
          {rootNode.id}
        </div>
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '13px', color: 'var(--mm-accent)', marginTop: '2px', fontWeight: 600 }}>
          {rootNode.amount}
        </div>
      </div>

      {/* SVG Connector from Root to Level 1 */}
      <svg width="340" height="40" style={{ overflow: 'visible' }}>
        <line x1="170" y1="0" x2="170" y2="15" stroke="var(--mm-border-strong)" strokeWidth="1.5" />
        <line x1="85" y1="15" x2="255" y2="15" stroke="var(--mm-border-strong)" strokeWidth="1.5" />
        <line x1="85" y1="15" x2="85" y2="40" stroke="var(--mm-border-strong)" strokeWidth="1.5" />
        <line x1="255" y1="15" x2="255" y2="40" stroke="var(--mm-border-strong)" strokeWidth="1.5" />
      </svg>

      {/* Level 1: P-101 and P-102 */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '30px', width: '100%' }}>
        {/* Child 1 (P-101) */}
        {rootNode.children && rootNode.children[0] && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div
              onClick={() => onSelectNode(rootNode.children![0])}
              className={`mm-panel ${selectedId === rootNode.children![0].id ? 'selected' : ''}`}
              style={{
                width: '140px',
                padding: '9px 12px',
                textAlign: 'center',
                cursor: 'pointer',
                borderColor: selectedId === rootNode.children![0].id ? 'var(--mm-burnt-amber)' : 'var(--mm-border)',
                background: selectedId === rootNode.children![0].id ? 'rgba(185, 157, 115, 0.12)' : 'var(--mm-surface-2)',
              }}
            >
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, color: 'var(--mm-text)' }}>
                {rootNode.children[0].id}
              </div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: 'var(--mm-accent)', marginTop: '2px', fontWeight: 600 }}>
                {rootNode.children[0].amount}
              </div>
            </div>

            {/* SVG Connector from P-101 to Level 2 (P-101A and P-101B) */}
            <svg width="200" height="40" style={{ overflow: 'visible' }}>
              <line x1="100" y1="0" x2="100" y2="15" stroke="var(--mm-border-strong)" strokeWidth="1.5" />
              <line x1="50" y1="15" x2="150" y2="15" stroke="var(--mm-border-strong)" strokeWidth="1.5" />
              <line x1="50" y1="15" x2="50" y2="40" stroke="var(--mm-border-strong)" strokeWidth="1.5" />
              <line x1="150" y1="15" x2="150" y2="40" stroke="var(--mm-border-strong)" strokeWidth="1.5" />
            </svg>

            {/* Level 2: P-101A and P-101B */}
            <div style={{ display: 'flex', gap: '16px' }}>
              {rootNode.children[0].children?.map((subChild) => (
                <div
                  key={subChild.id}
                  onClick={() => onSelectNode(subChild)}
                  className={`mm-panel ${selectedId === subChild.id ? 'selected' : ''}`}
                  style={{
                    width: '100px',
                    padding: '8px 10px',
                    textAlign: 'center',
                    cursor: 'pointer',
                    borderColor: selectedId === subChild.id ? 'var(--mm-burnt-amber)' : 'var(--mm-border)',
                    background: selectedId === subChild.id ? 'rgba(185, 157, 115, 0.12)' : 'var(--mm-surface-2)',
                  }}
                >
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', fontWeight: 700, color: 'var(--mm-text)' }}>
                    {subChild.id}
                  </div>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '11px', color: 'var(--mm-accent)', marginTop: '1px' }}>
                    {subChild.amount}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Child 2 (P-102) */}
        {rootNode.children && rootNode.children[1] && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div
              onClick={() => onSelectNode(rootNode.children![1])}
              className={`mm-panel ${selectedId === rootNode.children![1].id ? 'selected' : ''}`}
              style={{
                width: '140px',
                padding: '9px 12px',
                textAlign: 'center',
                cursor: 'pointer',
                borderColor: selectedId === rootNode.children![1].id ? 'var(--mm-burnt-amber)' : 'var(--mm-border)',
                background: selectedId === rootNode.children![1].id ? 'rgba(185, 157, 115, 0.12)' : 'var(--mm-surface-2)',
              }}
            >
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, color: 'var(--mm-text)' }}>
                {rootNode.children[1].id}
              </div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', color: 'var(--mm-accent)', marginTop: '2px', fontWeight: 600 }}>
                {rootNode.children[1].amount}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
