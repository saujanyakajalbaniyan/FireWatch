import React from 'react';
import { Search, Flame } from 'lucide-react';

export default function RiskAnalysis({ riskAssessments, clusters }) {
  if (!riskAssessments || riskAssessments.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon"><Search size={32} /></div>
        <p>Waiting for AI risk analysis...</p>
      </div>
    );
  }

  return (
    <div className="sidebar-content">
      {/* Cluster Summary */}
      {clusters && clusters.length > 0 && (
        <div className="alert-card" style={{ borderLeft: '3px solid var(--fire-orange)' }}>
          <div className="alert-header">
            <span className="alert-title"><Flame size={16} style={{marginRight: '6px'}} /> Fire Clusters Detected</span>
            <span className="alert-badge high">{clusters.length} clusters</span>
          </div>
          <p className="alert-message">
            AI has identified {clusters.length} fire cluster{clusters.length > 1 ? 's' : ''} with multiple
            fires in close proximity, indicating potential wildfire spread.
          </p>
        </div>
      )}

      {/* Regional Risk Cards */}
      {riskAssessments.map((risk, idx) => (
        <div key={idx} className="risk-card">
          <div className="risk-header">
            <span className="risk-region">{risk.region}</span>
            <div className={`risk-score ${risk.risk_level}`}>
              {risk.risk_score}
            </div>
          </div>

          <div className="risk-bar">
            <div
              className={`risk-bar-fill ${risk.risk_level}`}
              style={{ width: `${risk.risk_score}%` }}
            />
          </div>

          <div className="risk-stats">
            <div className="risk-stat">
              <div className="risk-stat-value">{risk.fire_count}</div>
              <div className="risk-stat-label">Fires</div>
            </div>
            <div className="risk-stat">
              <div className="risk-stat-value">{risk.cluster_count}</div>
              <div className="risk-stat-label">Clusters</div>
            </div>
            <div className="risk-stat">
              <div className="risk-stat-value">{risk.avg_confidence}%</div>
              <div className="risk-stat-label">Confidence</div>
            </div>
          </div>

          <p className="risk-assessment">{risk.assessment}</p>
        </div>
      ))}
    </div>
  );
}
