import React, { useCallback, useEffect, useState } from 'react';
import { API_BASE } from '../config';
import { ClipboardList, Flame, BarChart2, AlertTriangle, Clock, CheckCircle } from 'lucide-react';

const severityColor = {
  critical: 'var(--severity-critical)',
  high: 'var(--severity-high)',
  moderate: 'var(--severity-moderate)',
  low: 'var(--severity-low)',
};

export default function FireHistory({ fires }) {
  const [history, setHistory] = useState([]);
  const [alertHistory, setAlertHistory] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [activeTab, setActiveTab] = useState('fires');
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [searchText, setSearchText] = useState('');

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/history`);
      const data = await res.json();
      setHistory(data.history || []);
    } catch (err) {
      console.error('Failed to fetch history:', err);
    }
  }, []);

  const fetchAlertHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/alert-history?limit=200`);
      const data = await res.json();
      setAlertHistory(data.alerts || []);
    } catch (err) {
      console.error('Failed to fetch alert history:', err);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchHistory();
      fetchAlertHistory();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchAlertHistory, fetchHistory]);

  // Current fires as table rows
  const filteredFires = fires.filter(f => {
    if (filterSeverity !== 'all' && f.severity !== filterSeverity) return false;
    if (searchText) {
      const search = searchText.toLowerCase();
      return (
        f.satellite?.toLowerCase().includes(search) ||
        f.acq_date?.includes(search) ||
        String(f.latitude).includes(search) ||
        String(f.longitude).includes(search)
      );
    }
    return true;
  });

  return (
    <div className="history-page">
      <div className="page-header">
        <h1 className="page-title"><ClipboardList size={28} style={{marginRight: '8px'}} /> Fire History Log</h1>
        <p className="page-subtitle">Track all fire detections and alerts over time</p>
      </div>

      {/* Tab Switcher */}
      <div className="history-tabs">
        <button
          className={`htab ${activeTab === 'fires' ? 'active' : ''}`}
          onClick={() => setActiveTab('fires')}
        >
          <Flame size={16} /> Current Fires ({fires.length})
        </button>
        <button
          className={`htab ${activeTab === 'snapshots' ? 'active' : ''}`}
          onClick={() => setActiveTab('snapshots')}
        >
          <BarChart2 size={16} /> Detection Snapshots ({history.length})
        </button>
        <button
          className={`htab ${activeTab === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveTab('alerts')}
        >
          <AlertTriangle size={16} /> Alert History ({alertHistory.length})
        </button>

      </div>

      {/* Current Fires Table */}
      {activeTab === 'fires' && (
        <div className="history-section">
          <div className="history-filters">
            <input
              type="text"
              className="history-search"
              placeholder="Search by location, satellite, date..."
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
            />
            <select
              className="history-select"
              value={filterSeverity}
              onChange={e => setFilterSeverity(e.target.value)}
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="moderate">Moderate</option>
              <option value="low">Low</option>
            </select>
          </div>

          <div className="history-table-wrapper">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Latitude</th>
                  <th>Longitude</th>
                  <th>Confidence</th>
                  <th>FRP (MW)</th>
                  <th>Brightness (K)</th>
                  <th>Satellite</th>
                  <th>Date</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {filteredFires.slice(0, 200).map((fire, idx) => (
                  <tr key={idx}>
                    <td>
                      <span className="severity-dot" style={{ background: severityColor[fire.severity] }}></span>
                      {fire.severity}
                    </td>
                    <td>{fire.latitude?.toFixed(3)}</td>
                    <td>{fire.longitude?.toFixed(3)}</td>
                    <td>{fire.confidence}%</td>
                    <td>{fire.frp}</td>
                    <td>{fire.brightness}</td>
                    <td>{fire.satellite}</td>
                    <td>{fire.acq_date}</td>
                    <td>{fire.acq_time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredFires.length === 0 && (
              <div className="empty-state" style={{ padding: '40px' }}>
                <p>No fires match the current filters.</p>
              </div>
            )}
          </div>
          <div className="history-footer">
            Showing {Math.min(filteredFires.length, 200)} of {filteredFires.length} fires
          </div>
        </div>
      )}

      {/* Detection Snapshots */}
      {activeTab === 'snapshots' && (
        <div className="history-section">
          <div className="snapshot-grid">
            {history.map((snap, idx) => (
              <div key={idx} className="snapshot-card">
                <div className="snapshot-header">
                  <span className="snapshot-time">
                    <Clock size={14} style={{display:'inline', marginRight:'4px'}} /> {new Date(snap.timestamp).toLocaleString()}
                  </span>
                  <span className="snapshot-count fire-text">{snap.total_fires} fires</span>
                </div>
                <div className="snapshot-stats">
                  <div className="snapshot-stat">
                    <span style={{ color: severityColor.critical }}>{snap.critical}</span>
                    <small>Critical</small>
                  </div>
                  <div className="snapshot-stat">
                    <span style={{ color: severityColor.high }}>{snap.high}</span>
                    <small>High</small>
                  </div>
                  <div className="snapshot-stat">
                    <span>{snap.avg_confidence}%</span>
                    <small>Avg Conf</small>
                  </div>
                  <div className="snapshot-stat">
                    <span>{snap.avg_frp}</span>
                    <small>Avg FRP</small>
                  </div>
                </div>
              </div>
            ))}
            {history.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-icon"><ClipboardList size={32} /></div>
                <p>No detection snapshots yet. Data will appear after the first scan.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Alert History */}
      {activeTab === 'alerts' && (
        <div className="history-section">
          <div className="alert-history-list">
            {alertHistory.map((alert, idx) => (
              <div key={idx} className={`alert-card ${alert.level}`}>
                <div className="alert-header">
                  <span className="alert-title">{alert.title}</span>
                  <span className={`alert-badge ${alert.level}`}>{alert.level}</span>
                </div>
                <p className="alert-message">{alert.message}</p>
                <div className="alert-time">
                  <Clock size={14} style={{display:'inline', marginRight:'4px'}} /> {alert.logged_at ? new Date(alert.logged_at).toLocaleString() : 'N/A'}
                </div>
              </div>
            ))}
            {alertHistory.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-icon"><CheckCircle size={32} /></div>
                <p>No alerts in history.</p>
              </div>
            )}
          </div>
        </div>
      )}


    </div>
  );
}
