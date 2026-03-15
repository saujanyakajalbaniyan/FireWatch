import React from 'react';
import { NavLink } from 'react-router-dom';

export default function Header({ lastUpdated, isFetching, totalFires, onRefresh }) {
  return (
    <header className="header">
      <div className="header-brand">
        <div className="header-logo">🔥</div>
        <div>
          <div className="header-title">FireWatch AI</div>
          <div className="header-subtitle">NASA Satellite Fire Detection</div>
        </div>
      </div>

      <nav className="header-nav">
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`} end>
          🗺️ Dashboard
        </NavLink>
        <NavLink to="/upload" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          📸 Upload
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          📋 History
        </NavLink>
        <NavLink to="/regions" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          🌍 Regions
        </NavLink>
        <NavLink to="/visualizations" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          📊 Charts
        </NavLink>
        <NavLink to="/about" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          ℹ️ About
        </NavLink>
      </nav>

      <div className="header-status">
        <div className="status-indicator">
          <span className={`status-dot ${isFetching ? 'fetching' : ''}`}></span>
          {isFetching ? 'Fetching...' : `${totalFires} fires`}
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
