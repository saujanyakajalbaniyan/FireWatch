import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import Header from './components/Header';
import FireMap from './components/FireMap';
import StatsPanel from './components/StatsPanel';
import AlertsPanel from './components/AlertsPanel';
import RiskAnalysis from './components/RiskAnalysis';
import ImageUpload from './components/ImageUpload';
import FireHistory from './components/FireHistory';
import RegionSelector from './components/RegionSelector';
import DataVisualization from './components/DataVisualization';
import NotificationToast from './components/NotificationToast';
import AboutPage from './components/AboutPage';

const API_BASE = 'http://localhost:5000/api';

function Dashboard({ fires, analytics, alerts, riskAssessments, clusters }) {
  const [activeTab, setActiveTab] = useState('alerts');

  return (
    <>
      <div className="main-content">
        <FireMap fires={fires} />
        <StatsPanel analytics={analytics} />
      </div>

      <div className="sidebar">
        <div className="sidebar-tabs">
          <button
            className={`sidebar-tab ${activeTab === 'alerts' ? 'active' : ''}`}
            onClick={() => setActiveTab('alerts')}
          >
            ⚠️ Alerts {alerts.length > 0 && `(${alerts.length})`}
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'risk' ? 'active' : ''}`}
            onClick={() => setActiveTab('risk')}
          >
            🧠 AI Risk
          </button>
        </div>

        {activeTab === 'alerts' && <AlertsPanel alerts={alerts} />}
        {activeTab === 'risk' && (
          <RiskAnalysis riskAssessments={riskAssessments} clusters={clusters} />
        )}
      </div>
    </>
  );
}

function FullPageWrapper({ children }) {
  return <div className="full-page-content">{children}</div>;
}

function App() {
  const [fires, setFires] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [riskAssessments, setRiskAssessments] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isFetching, setIsFetching] = useState(false);
  const [notifications, setNotifications] = useState([]);

  const fetchData = useCallback(async () => {
    setIsFetching(true);
    try {
      const [firesRes, analyticsRes, riskRes, alertsRes] = await Promise.all([
        fetch(`${API_BASE}/fires?limit=2000`),
        fetch(`${API_BASE}/analytics`),
        fetch(`${API_BASE}/risk-analysis`),
        fetch(`${API_BASE}/alerts?limit=30`),
      ]);

      if (firesRes.ok) {
        const data = await firesRes.json();
        setFires(data.fires || []);
        setLastUpdated(data.last_updated);
      }

      if (analyticsRes.ok) {
        const data = await analyticsRes.json();
        setAnalytics(data.analytics || null);
      }

      if (riskRes.ok) {
        const data = await riskRes.json();
        setRiskAssessments(data.risk_assessments || []);
        setClusters(data.clusters || []);
      }

      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlerts(data.alerts || []);

        // Add critical alerts as notifications
        const critical = (data.alerts || []).filter(a => a.level === 'critical');
        if (critical.length > 0) {
          setNotifications(prev => [
            ...critical.slice(0, 3).map(a => ({
              id: Date.now() + Math.random(),
              ...a,
            })),
            ...prev,
          ].slice(0, 5));
        }
      }
    } catch (err) {
      console.error('Failed to fetch data:', err);
    } finally {
      setIsFetching(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 300000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const dismissNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  return (
    <BrowserRouter>
      <div className="app">
        <Header
          lastUpdated={lastUpdated}
          isFetching={isFetching}
          totalFires={fires.length}
          onRefresh={fetchData}
        />

        <Routes>
          <Route
            path="/"
            element={
              <Dashboard
                fires={fires}
                analytics={analytics}
                alerts={alerts}
                riskAssessments={riskAssessments}
                clusters={clusters}
              />
            }
          />
          <Route path="/upload" element={<FullPageWrapper><ImageUpload /></FullPageWrapper>} />
          <Route path="/history" element={<FullPageWrapper><FireHistory fires={fires} /></FullPageWrapper>} />
          <Route path="/regions" element={<FullPageWrapper><RegionSelector fires={fires} /></FullPageWrapper>} />
          <Route path="/visualizations" element={<FullPageWrapper><DataVisualization /></FullPageWrapper>} />
          <Route path="/about" element={<FullPageWrapper><AboutPage /></FullPageWrapper>} />
        </Routes>

        <NotificationToast
          notifications={notifications}
          onDismiss={dismissNotification}
        />
      </div>
    </BrowserRouter>
  );
}

export default App;
