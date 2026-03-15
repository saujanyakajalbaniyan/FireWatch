import React from 'react';

export default function AlertsPanel({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">✅</div>
        <p>No active alerts at this time.</p>
      </div>
    );
  }

  return (
    <div className="sidebar-content">
      {alerts.map((alert, idx) => (
        <div key={idx} className={`alert-card ${alert.level}`}>
          <div className="alert-header">
            <span className="alert-title">{alert.title}</span>
            <span className={`alert-badge ${alert.level}`}>{alert.level}</span>
          </div>
          <p className="alert-message">{alert.message}</p>
          <div className="alert-time">
            📍 {alert.latitude?.toFixed(2)}, {alert.longitude?.toFixed(2)} &nbsp;|&nbsp;
            🕐 {alert.timestamp ? new Date(alert.timestamp).toLocaleString() : 'N/A'}
          </div>
        </div>
      ))}
    </div>
  );
}
