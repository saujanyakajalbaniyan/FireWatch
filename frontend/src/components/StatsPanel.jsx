import React from 'react';

export default function StatsPanel({ analytics }) {
  if (!analytics) {
    return null;
  }

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
