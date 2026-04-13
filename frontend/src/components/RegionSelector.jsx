import React, { useCallback, useEffect, useState } from 'react';
import { Globe, MapPin, MousePointerClick } from 'lucide-react';
import { API_BASE } from '../config';

const regionIcon = <MapPin size={20} style={{display:'inline', marginRight:'4px'}} />;

const severityColor = {
  critical: 'var(--severity-critical)',
  high: 'var(--severity-high)',
  moderate: 'var(--severity-moderate)',
  low: 'var(--severity-low)',
  none: 'var(--text-muted)',
};

export default function RegionSelector({ fires }) {
  const [regions, setRegions] = useState([]);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [regionFires, setRegionFires] = useState([]);

  const fetchRegions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/regions`);
      const data = await res.json();
      setRegions(data.regions || []);
    } catch (err) {
      console.error('Failed to fetch regions:', err);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchRegions();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchRegions]);

  const selectRegion = (region) => {
    setSelectedRegion(region);
    // Filter fires for this region using bbox
    const [west, south, east, north] = region.bbox;
    const filtered = fires.filter(
      f => f.longitude >= west && f.longitude <= east &&
           f.latitude >= south && f.latitude <= north
    );
    setRegionFires(filtered);
  };

  return (
    <div className="regions-page">
      <div className="page-header">
        <h1 className="page-title"><Globe size={28} style={{marginRight: '8px'}} /> Region Selection</h1>
        <p className="page-subtitle">Select a region to view fire activity and detailed analysis</p>
      </div>

      <div className="regions-layout">
        {/* Region Cards Grid */}
        <div className="regions-grid">
          {regions.map((region, idx) => (
            <div
              key={idx}
              className={`region-card ${selectedRegion?.name === region.name ? 'selected' : ''}`}
              onClick={() => selectRegion(region)}
            >
              <div className="region-card-header">
                <span className="region-emoji">{regionIcon}</span>
                <h3>{region.name}</h3>
              </div>

              <div className="region-fire-count">
                <span className="region-count-value fire-text">{region.fire_count}</span>
                <span className="region-count-label">active fires</span>
              </div>

              <div className="region-details">
                <div className="region-detail-row">
                  <span>Avg FRP</span>
                  <span>{region.avg_frp} MW</span>
                </div>
                <div className="region-detail-row">
                  <span>Dominant</span>
                  <span style={{ color: severityColor[region.dominant_severity] }}>
                    {region.dominant_severity?.toUpperCase() || 'N/A'}
                  </span>
                </div>
              </div>

              {/* Severity mini bar */}
              <div className="region-severity-bar">
                {['critical', 'high', 'moderate', 'low'].map(sev => {
                  const count = region.severity_distribution?.[sev] || 0;
                  const pct = region.fire_count > 0 ? (count / region.fire_count * 100) : 0;
                  return pct > 0 ? (
                    <div
                      key={sev}
                      className="severity-segment"
                      style={{
                        width: `${pct}%`,
                        background: severityColor[sev],
                      }}
                      title={`${sev}: ${count}`}
                    ></div>
                  ) : null;
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Selected Region Detail */}
        {selectedRegion && (
          <div className="region-detail-panel">
            <h2>{regionIcon} {selectedRegion.name}</h2>
            <p className="region-fires-summary">
              {regionFires.length} fires detected in this region
            </p>

            <div className="region-stats-row">
              <div className="region-stat-box">
                <div className="region-stat-val" style={{ color: severityColor.critical }}>
                  {regionFires.filter(f => f.severity === 'critical').length}
                </div>
                <div className="region-stat-lbl">Critical</div>
              </div>
              <div className="region-stat-box">
                <div className="region-stat-val" style={{ color: severityColor.high }}>
                  {regionFires.filter(f => f.severity === 'high').length}
                </div>
                <div className="region-stat-lbl">High</div>
              </div>
              <div className="region-stat-box">
                <div className="region-stat-val" style={{ color: severityColor.moderate }}>
                  {regionFires.filter(f => f.severity === 'moderate').length}
                </div>
                <div className="region-stat-lbl">Moderate</div>
              </div>
              <div className="region-stat-box">
                <div className="region-stat-val" style={{ color: severityColor.low }}>
                  {regionFires.filter(f => f.severity === 'low').length}
                </div>
                <div className="region-stat-lbl">Low</div>
              </div>
            </div>

            {/* Region fire list */}
            <div className="region-fire-list">
              <h3>Fire Detections</h3>
              {regionFires.slice(0, 30).map((fire, idx) => (
                <div key={idx} className="region-fire-item">
                  <span className="severity-dot" style={{ background: severityColor[fire.severity] }}></span>
                  <span>{fire.latitude?.toFixed(2)}, {fire.longitude?.toFixed(2)}</span>
                  <span className="region-fire-conf">{fire.confidence}%</span>
                  <span className="region-fire-frp">{fire.frp} MW</span>
                </div>
              ))}
              {regionFires.length > 30 && (
                <p className="region-more">...and {regionFires.length - 30} more</p>
              )}
            </div>
          </div>
        )}

        {!selectedRegion && (
          <div className="region-detail-panel placeholder">
            <div className="empty-state">
              <div className="empty-state-icon"><MousePointerClick size={32} /></div>
              <h3>Select a Region</h3>
              <p>Click on a region card to view detailed fire analysis</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
