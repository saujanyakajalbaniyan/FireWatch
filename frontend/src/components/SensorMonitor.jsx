import React, { useEffect, useState } from 'react';
import { API_BASE } from '../config';

function MiniLineChart({ points, keyName, color, label }) {
  if (!points?.length) return null;
  const values = points.map((p) => Number(p[keyName] || 0));
  const min = Math.min(...values);
  const max = Math.max(...values, min + 1);
  const path = values
    .map((v, i) => {
      const x = (i / Math.max(values.length - 1, 1)) * 100;
      const y = 100 - ((v - min) / (max - min)) * 100;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="metric-card">
      <h3>{label}</h3>
      <svg viewBox="0 0 100 100" className="sensor-chart">
        <polyline fill="none" stroke={color} strokeWidth="2.2" points={path} />
      </svg>
      <p>Latest: {values[values.length - 1]}</p>
    </div>
  );
}

export default function SensorMonitor() {
  const [sensor, setSensor] = useState({ temperature_c: 32, smoke_ppm: 20, humidity: 45 });
  const [latest, setLatest] = useState(null);
  const [history, setHistory] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [sending, setSending] = useState(false);

  const submitSensor = async () => {
    setSending(true);
    try {
      const res = await fetch(`${API_BASE}/sensors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...sensor,
          location: { latitude: 37.7749, longitude: -122.4194 },
        }),
      });
      const data = await res.json();
      setLatest(data.reading);
      if (data.reading) {
        setHistory((prev) => [data.reading, ...prev].slice(0, 120));
      }
    } finally {
      setSending(false);
    }
  };

  useEffect(() => {
    const loadLatest = async () => {
      const [sensorRes, predRes] = await Promise.all([
        fetch(`${API_BASE}/sensors`),
        fetch(`${API_BASE}/predictions`),
      ]);
      const data = await sensorRes.json();
      setLatest(data.reading);
      setHistory(data.history || []);
      if (predRes.ok) {
        setPrediction(await predRes.json());
      }
    };
    loadLatest();
  }, []);

  return (
    <div className="sensor-page">
      <div className="page-header">
        <h1 className="page-title">Sensor Data Monitor</h1>
        <p className="page-subtitle">Temperature and smoke telemetry with automatic risk scoring</p>
      </div>

      <div className="sensor-layout">
        <div className="sensor-form">
          <label>Temperature (C)</label>
          <input
            type="number"
            value={sensor.temperature_c}
            onChange={(e) => setSensor((prev) => ({ ...prev, temperature_c: Number(e.target.value) }))}
          />

          <label>Smoke (ppm)</label>
          <input
            type="number"
            value={sensor.smoke_ppm}
            onChange={(e) => setSensor((prev) => ({ ...prev, smoke_ppm: Number(e.target.value) }))}
          />

          <label>Humidity (%)</label>
          <input
            type="number"
            value={sensor.humidity}
            onChange={(e) => setSensor((prev) => ({ ...prev, humidity: Number(e.target.value) }))}
          />

          <button className="btn-analyze" onClick={submitSensor} disabled={sending}>
            {sending ? 'Sending...' : 'Send Sensor Reading'}
          </button>
        </div>

        <div className="sensor-output">
          <h3>Latest Reading</h3>
          {latest ? (
            <div className="sensor-card">
              <p>Temperature: {latest.temperature_c} C</p>
              <p>Smoke: {latest.smoke_ppm} ppm</p>
              <p>Humidity: {latest.humidity}%</p>
              <p>Risk Score: {latest.risk_score}</p>
              <p className={`status-chip ${latest.level}`}>Level: {latest.level}</p>
              <p>Time: {new Date(latest.timestamp).toLocaleString()}</p>
            </div>
          ) : (
            <p>No sensor data yet.</p>
          )}

          <div className="sensor-charts-grid">
            <MiniLineChart points={[...history].reverse()} keyName="temperature_c" color="#ef4444" label="Temperature vs Time" />
            <MiniLineChart points={[...history].reverse()} keyName="smoke_ppm" color="#f59e0b" label="Smoke vs Time" />
            <MiniLineChart points={[...history].reverse()} keyName="risk_score" color="#22c55e" label="Risk Score vs Time" />
          </div>

          {prediction && (
            <div className="metric-card" style={{ marginTop: '10px' }}>
              <h3>Future Prediction</h3>
              <p>30 min Risk Score: {prediction.forecast?.risk_score_30m}</p>
              <p className={`status-chip ${prediction.forecast?.risk_level_30m}`}>Level: {prediction.forecast?.risk_level_30m}</p>
              <p>Temperature Trend: {prediction.trends?.temperature_per_step}</p>
              <p>Smoke Trend: {prediction.trends?.smoke_per_step}</p>
              <p>Pattern (Hot + Smoky): {prediction.patterns?.hot_and_smoky}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
