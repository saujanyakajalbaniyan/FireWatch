import React, { useCallback, useEffect, useState } from 'react';
import { Info, Flame, Zap, CheckCircle, Clock, RefreshCw, Satellite, Wrench, Code, Layout, Map, Brain, Image, Radio, Sparkles, Camera, Bell, BarChart2, ClipboardList, BookOpen, AlertCircle } from 'lucide-react';
import { API_BASE } from '../config';

export default function AboutPage() {
  const [status, setStatus] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      if (res.ok) setStatus(await res.json());
    } catch (err) {
      console.error('Status fetch failed:', err);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchStatus();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchStatus]);

  return (
    <div className="about-page">
      <div className="page-header">
        <h1 className="page-title"><Info size={28} style={{marginRight: '8px'}} /> About FireWatch AI</h1>
        <p className="page-subtitle">AI-Driven Forest Fire Detection System</p>
      </div>

      <div className="about-grid">
        {/* System Overview */}
        <div className="about-card hero-card">
          <div className="about-hero-icon"><Flame size={48} /></div>
          <h2>FireWatch AI</h2>
          <p>
            An advanced forest fire detection and monitoring platform that leverages
            NASA satellite data and artificial intelligence to detect, analyze, and
            alert on active fires worldwide in near real-time.
          </p>
        </div>

        {/* System Status */}
        <div className="about-card">
          <h3><Zap size={20} style={{marginRight: '8px', display: 'inline'}} /> System Status</h3>
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
                  {status.analysis_available ? <><CheckCircle size={14} style={{display:'inline'}} /> Available</> : <><Clock size={14} style={{display:'inline'}} /> Pending</>}
                </span>
              </div>
              <div className="status-item">
                <span className="status-label">Fetching</span>
                <span className="status-val">
                  {status.is_fetching ? <><RefreshCw size={14} style={{display:'inline'}} /> In progress</> : <><CheckCircle size={14} style={{display:'inline'}} /> Idle</>}
                </span>
              </div>
            </div>
          ) : (
            <p className="about-muted">Loading status...</p>
          )}
        </div>

        {/* Data Sources */}
        <div className="about-card">
          <h3><Satellite size={20} style={{marginRight: '8px', display: 'inline'}} /> Data Sources</h3>
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
          <h3><Wrench size={20} style={{marginRight: '8px', display: 'inline'}} /> Technology Stack</h3>
          <div className="tech-grid">
            <div className="tech-item">
              <span className="tech-icon"><Layout size={20} /></span>
              <span>React + Vite</span>
            </div>
            <div className="tech-item">
              <span className="tech-icon"><Code size={20} /></span>
              <span>Python Flask</span>
            </div>
            <div className="tech-item">
              <span className="tech-icon"><Map size={20} /></span>
              <span>Leaflet Maps</span>
            </div>
            <div className="tech-item">
              <span className="tech-icon"><Brain size={20} /></span>
              <span>NumPy + Scikit-learn</span>
            </div>
            <div className="tech-item">
              <span className="tech-icon"><Image size={20} /></span>
              <span>Pillow (Image AI)</span>
            </div>
            <div className="tech-item">
              <span className="tech-icon"><Radio size={20} /></span>
              <span>WebSocket</span>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="about-card">
          <h3><Sparkles size={20} style={{marginRight: '8px', display: 'inline'}} /> Key Features</h3>
          <div className="about-list">
            <div className="about-list-item">
              <strong><Map size={16} style={{display:'inline', marginRight: '4px'}} /> Live Fire Map</strong>
              <p>Interactive world map with color-coded fire markers showing severity, confidence, and FRP.</p>
            </div>
            <div className="about-list-item">
              <strong><Camera size={16} style={{display:'inline', marginRight: '4px'}} /> Image Analysis</strong>
              <p>Upload images for AI-powered fire and smoke detection using color histograms and texture analysis.</p>
            </div>
            <div className="about-list-item">
              <strong><Bell size={16} style={{display:'inline', marginRight: '4px'}} /> Alert System</strong>
              <p>Real-time dashboard, email, and push notifications when critical fires are detected.</p>
            </div>
            <div className="about-list-item">
              <strong><BarChart2 size={16} style={{display:'inline', marginRight: '4px'}} /> Data Visualization</strong>
              <p>Interactive charts showing severity distribution, regional density, FRP analysis, and trends.</p>
            </div>
            <div className="about-list-item">
              <strong><Brain size={16} style={{display:'inline', marginRight: '4px'}} /> AI Risk Analysis</strong>
              <p>Machine learning-powered regional risk assessments with natural-language summaries.</p>
            </div>
            <div className="about-list-item">
              <strong><ClipboardList size={16} style={{display:'inline', marginRight: '4px'}} /> Fire History</strong>
              <p>Complete log of all fire detections and alerts with filtering and search capabilities.</p>
            </div>
          </div>
        </div>

        {/* Metrics Glossary */}
        <div className="about-card">
          <h3><BookOpen size={20} style={{marginRight: '8px', display: 'inline'}} /> Metrics Glossary</h3>
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
              <p>Critical (<AlertCircle size={12} color='red' style={{display:'inline'}}/>), High (<AlertCircle size={12} color='orange' style={{display:'inline'}}/>), Moderate (<AlertCircle size={12} color='yellow' style={{display:'inline'}}/>), Low (<AlertCircle size={12} color='green' style={{display:'inline'}}/>) — based on combined FRP, confidence, and brightness scores.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
