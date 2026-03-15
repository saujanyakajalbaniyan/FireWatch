import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:5000/api';

export default function AboutPage() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      if (res.ok) setStatus(await res.json());
    } catch (err) {
      console.error('Status fetch failed:', err);
    }
  };

  return (
    <div className="about-page">
      <div className="page-header">
        <h1 className="page-title">ℹ️ About FireWatch AI</h1>
        <p className="page-subtitle">AI-Driven Forest Fire Detection System</p>
      </div>

      <div className="about-grid">
        {/* System Overview */}
        <div className="about-card hero-card">
          <div className="about-hero-icon">🔥</div>
          <h2>FireWatch AI</h2>
          <p>
            An advanced forest fire detection and monitoring platform that leverages
            NASA satellite data and artificial intelligence to detect, analyze, and
            alert on active fires worldwide in near real-time.
          </p>
        </div>

        {/* System Status */}
        <div className="about-card">
          <h3>⚡ System Status</h3>
          {status ? (
            <div className="status-grid">
              <div className="status-item">
                <span className="status-label">Server</span>
                <span className="status-val online">● Running</span>
              </div>
              <div className="status-item">
                <span className="status-label">Active Fires</span>
                <span className="status-val">{status.total_fires}</span>
              </div>
              <div className="status-item">
                <span className="status-label">Last Updated</span>
                <span className="status-val">
                  {status.last_updated
                    ? new Date(status.last_updated).toLocaleString()
                    : 'N/A'}
                </span>
              </div>
              <div className="status-item">
                <span className="status-label">Analysis</span>
                <span className="status-val">
                  {status.analysis_available ? '✅ Available' : '⏳ Pending'}
                </span>
              </div>
              <div className="status-item">
                <span className="status-label">Fetching</span>
                <span className="status-val">
                  {status.is_fetching ? '🔄 In progress' : '✅ Idle'}
                </span>
              </div>
            </div>
          ) : (
            <p className="about-muted">Loading status...</p>
          )}
        </div>

        {/* Data Sources */}
        <div className="about-card">
          <h3>🛰️ Data Sources</h3>
          <div className="about-list">
            <div className="about-list-item">
              <strong>NASA FIRMS</strong>
              <p>Fire Information for Resource Management System — provides near real-time active fire data from satellite observations.</p>
            </div>
            <div className="about-list-item">
              <strong>VIIRS S-NPP</strong>
              <p>Visible Infrared Imaging Radiometer Suite on Suomi NPP satellite. 375m resolution thermal anomaly detection.</p>
            </div>
            <div className="about-list-item">
              <strong>MODIS</strong>
              <p>Moderate Resolution Imaging Spectroradiometer on Terra/Aqua satellites. 1km resolution fire detection.</p>
            </div>
          </div>
        </div>

        {/* Tech Stack */}
        <div className="about-card">
          <h3>🛠️ Technology Stack</h3>
          <div className="tech-grid">
            <div className="tech-item">
              <span className="tech-icon">⚛️</span>
              <span>React + Vite</span>
            </div>
            <div className="tech-item">
              <span className="tech-icon">🐍</span>
              <span>Python Flask</span>
            </div>
            <div className="tech-item">
              <span className="tech-icon">🗺️</span>
              <span>Leaflet Maps</span>
            </div>
            <div className="tech-item">
              <span className="tech-icon">🧠</span>
              <span>NumPy + Scikit-learn</span>
            </div>
            <div className="tech-item">
              <span className="tech-icon">🖼️</span>
              <span>Pillow (Image AI)</span>
            </div>
            <div className="tech-item">
              <span className="tech-icon">📡</span>
              <span>WebSocket</span>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="about-card">
          <h3>✨ Key Features</h3>
          <div className="about-list">
            <div className="about-list-item">
              <strong>🗺️ Live Fire Map</strong>
              <p>Interactive world map with color-coded fire markers showing severity, confidence, and FRP.</p>
            </div>
            <div className="about-list-item">
              <strong>📸 Image Analysis</strong>
              <p>Upload images for AI-powered fire and smoke detection using color histograms and texture analysis.</p>
            </div>
            <div className="about-list-item">
              <strong>🔔 Alert System</strong>
              <p>Real-time dashboard, email, and push notifications when critical fires are detected.</p>
            </div>
            <div className="about-list-item">
              <strong>📊 Data Visualization</strong>
              <p>Interactive charts showing severity distribution, regional density, FRP analysis, and trends.</p>
            </div>
            <div className="about-list-item">
              <strong>🧠 AI Risk Analysis</strong>
              <p>Machine learning-powered regional risk assessments with natural-language summaries.</p>
            </div>
            <div className="about-list-item">
              <strong>📋 Fire History</strong>
              <p>Complete log of all fire detections and alerts with filtering and search capabilities.</p>
            </div>
          </div>
        </div>

        {/* Metrics Glossary */}
        <div className="about-card">
          <h3>📖 Metrics Glossary</h3>
          <div className="about-list">
            <div className="about-list-item">
              <strong>FRP (Fire Radiative Power)</strong>
              <p>Measured in megawatts (MW). Indicates the rate of radiant heat output from a fire. Higher = more intense.</p>
            </div>
            <div className="about-list-item">
              <strong>Confidence</strong>
              <p>0–100% measure of how likely the detection is an actual fire vs false positive.</p>
            </div>
            <div className="about-list-item">
              <strong>Brightness Temperature</strong>
              <p>Measured in Kelvin (K). The thermal infrared brightness at the fire pixel.</p>
            </div>
            <div className="about-list-item">
              <strong>Severity Levels</strong>
              <p>Critical (🔴), High (🟠), Moderate (🟡), Low (🟢) — based on combined FRP, confidence, and brightness scores.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
