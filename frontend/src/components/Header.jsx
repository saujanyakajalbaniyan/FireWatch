import React from 'react';
import { NavLink } from 'react-router-dom';
import { Flame, Map, Camera, History, Globe, BarChart2, BellRing, Info, Video, Activity } from 'lucide-react';

export default function Header({ lastUpdated, isFetching, totalFires, socketStatus, onRefresh, voiceEnabled, onToggleVoice, onTestVoice }) {
  const syncLabel = {
    connected: 'Live sync',
    connecting: 'Syncing',
    degraded: 'Reconnect',
    offline: 'Offline',
  }[socketStatus] || 'Syncing';

  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo"><Flame size={24} /></div>
        <div>
          <div className="header-title">FireWatch AI</div>
          <div className="header-subtitle">NASA Satellite Fire Detection</div>
        </div>
      </div>

      <nav className="header-nav">
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end>
          <Map size={18} /> Dashboard
        </NavLink>
        <NavLink to="/upload" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Camera size={18} /> Footage Analysis
        </NavLink>
        <NavLink to="/live-feed" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Video size={18} /> Live Camera
        </NavLink>
        <NavLink to="/sensors" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Activity size={18} /> Sensors
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <History size={18} /> History
        </NavLink>
        <NavLink to="/regions" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Globe size={18} /> Regions
        </NavLink>
        <NavLink to="/visualizations" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <BarChart2 size={18} /> Charts
        </NavLink>

        <NavLink to="/alert-center" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <BellRing size={18} /> Alert Center
        </NavLink>
        <NavLink to="/about" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          <Info size={18} /> About
        </NavLink>
      </nav>

      <div className="header-status">
        <div className="status-indicator">
          <span className={`status-dot ${isFetching ? 'fetching' : ''}`}></span>
          {isFetching ? 'Fetching...' : `${totalFires} fires`}
        </div>

        <div className={`status-indicator sync ${socketStatus || 'connecting'}`}>
          <span className="status-dot"></span>
          {syncLabel}
        </div>



        <button className={`refresh-btn ${isFetching ? 'spinning' : ''}`} onClick={onRefresh}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M23 4v6h-6M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
          </svg>
          Refresh
        </button>
      </div>
    </header>
  );
}
