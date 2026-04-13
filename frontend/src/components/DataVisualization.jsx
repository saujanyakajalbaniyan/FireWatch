import React, { useState, useEffect } from 'react';
import { BarChart2, Flame, Globe, Sun, Zap, Target, AlertCircle, Brain, Thermometer } from 'lucide-react';
import { API_BASE } from '../config';


const COLORS = {
  critical: '#ef4444',
  high: '#f97316',
  moderate: '#f59e0b',
  low: '#22c55e',
};

function BarChart({ data, title, colorMap }) {
  const max = Math.max(...Object.values(data), 1);
  const total = Object.values(data).reduce((a, b) => a + b, 0);

  return (
    <div className="viz-card">
      <h3 className="viz-title">{title}</h3>
      <div className="bar-chart">
        {Object.entries(data).map(([label, value]) => (
          <div key={label} className="bar-row">
            <span className="bar-label">{label}</span>
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{
                  width: `${(value / max) * 100}%`,
                  background: colorMap?.[label] || 'var(--fire-gradient)',
                }}
              ></div>
            </div>
            <span className="bar-value">{value}</span>
            <span className="bar-pct">{total > 0 ? ((value / total) * 100).toFixed(0) : 0}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function DonutChart({ data, title }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  const colors = ['#f97316', '#3b82f6', '#22c55e', '#ef4444', '#a855f7'];
  let cumPct = 0;
  const segments = Object.entries(data).map(([label, value], idx) => {
    const pct = total > 0 ? (value / total) * 100 : 0;
    const start = cumPct;
    cumPct += pct;
    return { label, value, pct, start, color: colors[idx % colors.length] };
  });

  // Build conic-gradient
  let gradient = 'conic-gradient(';
  segments.forEach((seg, i) => {
    gradient += `${seg.color} ${seg.start}% ${seg.start + seg.pct}%`;
    if (i < segments.length - 1) gradient += ', ';
  });
  gradient += ')';

  return (
    <div className="viz-card">
      <h3 className="viz-title">{title}</h3>
      <div className="donut-container">
        <div className="donut-ring" style={{ background: gradient }}>
          <div className="donut-hole">
            <span className="donut-total">{total}</span>
            <span className="donut-label">Total</span>
          </div>
        </div>
        <div className="donut-legend">
          {segments.map(seg => (
            <div key={seg.label} className="legend-item">
              <span className="legend-dot" style={{ background: seg.color }}></span>
              <span className="legend-name">{seg.label}</span>
              <span className="legend-value">{seg.value} ({seg.pct.toFixed(0)}%)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TrendChart({ points, title }) {
  if (!points?.length) return null;
  const values = points.map((p) => Number(p.temperature_c || 0));
  const min = Math.min(...values);
  const max = Math.max(...values, min + 1);
  const line = values
    .map((v, i) => {
      const x = (i / Math.max(values.length - 1, 1)) * 100;
      const y = 100 - ((v - min) / (max - min)) * 100;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="viz-card">
      <h3 className="viz-title">{title}</h3>
      <svg viewBox="0 0 100 100" className="sensor-chart">
        <polyline fill="none" stroke="#ef4444" strokeWidth="2" points={line} />
      </svg>
      <p className="page-subtitle">Latest: {values[values.length - 1]} C</p>
    </div>
  );
}

export default function DataVisualization() {
  const [vizData, setVizData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const res = await fetch(`${API_BASE}/visualization-data`);
      if (res.ok) {
        const data = await res.json();
        setVizData(data);
      }
    } catch (err) {
      console.error('Failed to fetch viz data:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="viz-page">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading visualization data...</p>
        </div>
      </div>
    );
  }

  if (!vizData) {
    return (
      <div className="viz-page">
        <div className="empty-state">
          <div className="empty-state-icon"><BarChart2 size={32} /></div>
          <p>No data available for visualization.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="viz-page">
      <div className="page-header">
        <h1 className="page-title"><BarChart2 size={28} style={{marginRight: '8px'}} /> Data Visualization</h1>
        <p className="page-subtitle">
          Visual analytics for {vizData.total_fires} active fires
        </p>
      </div>

      <div className="viz-grid">
        <BarChart
          data={vizData.severity_distribution}
          title={<><Flame size={16} style={{display:'inline', marginRight:'4px'}} /> Severity Distribution</>}
          colorMap={COLORS}
        />

        <BarChart
          data={vizData.regional_distribution}
          title={<><Globe size={16} style={{display:'inline', marginRight:'4px'}} /> Fires by Region</>}
        />

        <DonutChart
          data={vizData.day_night}
          title={<><Sun size={16} style={{display:'inline', marginRight:'4px'}} /> Day vs Night Detections</>}
        />

        <BarChart
          data={vizData.frp_distribution}
          title={<><Zap size={16} style={{display:'inline', marginRight:'4px'}} /> Fire Radiative Power (MW)</>}
          colorMap={{
            '0-10': '#22c55e',
            '10-25': '#f59e0b',
            '25-50': '#f97316',
            '50-100': '#ef4444',
            '100+': '#dc2626',
          }}
        />

        <BarChart
          data={vizData.confidence_distribution}
          title={<><Target size={16} style={{display:'inline', marginRight:'4px'}} /> Detection Confidence</>}
          colorMap={{
            '0-25': '#ef4444',
            '25-50': '#f97316',
            '50-75': '#f59e0b',
            '75-100': '#22c55e',
          }}
        />

        <DonutChart
          data={vizData.severity_distribution}
          title={<><AlertCircle size={16} style={{display:'inline', marginRight:'4px'}} /> Severity Breakdown</>}
        />

        <DonutChart
          data={vizData.scene_distribution || { unknown: 0 }}
          title={<><Brain size={16} style={{display:'inline', marginRight:'4px'}} /> Scene Classification (Fire vs Sunlight / Smoke vs Fog)</>}
        />

        <TrendChart
          points={vizData.sensor_time_series || []}
          title={<><Thermometer size={16} style={{display:'inline', marginRight:'4px'}} /> Temperature vs Time</>}
        />
      </div>
    </div>
  );
}
