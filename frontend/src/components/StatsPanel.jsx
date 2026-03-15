import React from 'react';

const severityColors = {
  critical: 'var(--severity-critical)',
  high: 'var(--severity-high)',
  moderate: 'var(--severity-moderate)',
  low: 'var(--severity-low)',
};

export default function StatsPanel({ analytics }) {
  if (!analytics || !analytics.total_fires) {
    return null;
  }

  const { severity_distribution = {} } = analytics;
  const maxSev = Math.max(
    severity_distribution.critical || 0,
    severity_distribution.high || 0,
    severity_distribution.moderate || 0,
    severity_distribution.low || 0,
    1
  );

  return (
    <div className="stats-overlay">
      <div className="stat-card">
        <div className="stat-label">Active Fires</div>
        <div className="stat-value fire-text">{analytics.total_fires?.toLocaleString()}</div>
        <div className="stat-sub">Worldwide</div>
      </div>

      <div className="stat-card critical">
        <div className="stat-label">Critical</div>
        <div className="stat-value" style={{ color: 'var(--severity-critical)' }}>
          {analytics.critical_count || 0}
        </div>
        <div className="stat-sub">Immediate alert</div>
      </div>

      <div className="stat-card">
        <div className="stat-label">Avg Confidence</div>
        <div className="stat-value fire-text">{analytics.avg_confidence}%</div>
        <div className="stat-sub">Detection accuracy</div>
      </div>

      <div className="stat-card">
        <div className="stat-label">Avg FRP</div>
        <div className="stat-value fire-text">{analytics.avg_frp}</div>
        <div className="stat-sub">MW — intensity</div>
      </div>

      <div className="stat-card">
        <div className="stat-label">Total FRP</div>
        <div className="stat-value fire-text">{analytics.total_frp?.toLocaleString()}</div>
        <div className="stat-sub">MW cumulative</div>
      </div>
    </div>
  );
}
