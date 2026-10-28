import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  trend?: string;
  trendType?: 'good' | 'bad' | 'neutral';
  badge?: string;
  badgeType?: 'completed' | 'progress' | 'neutral';
  subtext?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  trend,
  trendType = 'good',
  badge,
  badgeType = 'completed',
  subtext,
}) => {
  return (
    <div className="mm-metric-card">
      <div className="mm-metric-value-row">
        <span className="mm-metric-val">{typeof value === 'number' ? value.toLocaleString() : value}</span>
        {trend && (
          <span className={`mm-metric-trend ${trendType === 'good' ? 'up-good' : 'up-bad'}`}>
            {trend}
          </span>
        )}
        {badge && (
          <span className={`mm-badge ${badgeType === 'completed' ? 'mm-badge-status-completed' : 'mm-badge-status-progress'}`}>
            {badge}
          </span>
        )}
      </div>
      <div>
        <div className="mm-metric-label">{label}</div>
        {subtext && <div style={{ fontSize: '10px', color: 'var(--mm-text-muted)', marginTop: '2px' }}>{subtext}</div>}
      </div>
    </div>
  );
};
