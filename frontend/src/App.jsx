import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { io } from 'socket.io-client';
import { AlertTriangle, Activity } from 'lucide-react';
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
import LiveCameraFeed from './components/LiveCameraFeed';
import SensorMonitor from './components/SensorMonitor';

import AlertCenter from './components/AlertCenter';
import VoiceAssistant from './components/VoiceAssistant';
import VoiceToggleFAB from './components/VoiceToggleFAB';
import { API_BASE } from './config';

const SOCKET_BASE = (import.meta.env.VITE_SOCKET_URL || API_BASE).replace(/\/api\/?$/, '');

function alertSignature(alert) {
  return [
    alert?.type || 'alert',
    alert?.level || 'low',
    alert?.title || '',
    alert?.timestamp || alert?.logged_at || '',
    alert?.latitude ?? '',
    alert?.longitude ?? '',
  ].join('|');
}

function normalizeAlert(alert) {
  if (!alert) return null;
  return {
    id: alert.id || alertSignature(alert),
    ...alert,
  };
}

function dedupeAlerts(list, limit = 30) {
  const seen = new Set();
  const items = [];

  for (const alert of list) {
    const normalized = normalizeAlert(alert);
    if (!normalized) continue;
    const key = normalized.id || alertSignature(normalized);
    if (seen.has(key)) continue;
    seen.add(key);
    items.push(normalized);
    if (items.length >= limit) break;
  }

  return items;
}

function mergeNotifications(existing, incoming, limit = 8) {
  return dedupeAlerts([...incoming, ...existing], limit);
}

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
            <AlertTriangle size={18} /> Alerts {alerts.length > 0 && `(${alerts.length})`}
          </button>
          <button
            className={`sidebar-tab ${activeTab === 'risk' ? 'active' : ''}`}
            onClick={() => setActiveTab('risk')}
          >
            <Activity size={18} /> AI Risk
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

function DashboardShell({ fires, analytics, alerts, riskAssessments, clusters, socketStatus, lastUpdated }) {
  const [activeTab, setActiveTab] = useState('alerts');

  const criticalAlerts = alerts.filter((alert) => alert.level === 'critical').length;
  const highAlerts = alerts.filter((alert) => alert.level === 'high').length;
  const fireCount = fires.length;
  const clusterCount = clusters.length;
  const updateLabel = lastUpdated ? new Date(lastUpdated).toLocaleString() : 'Waiting for first scan';

  const summaryCards = [
    { label: 'Active Fires', value: fireCount.toLocaleString(), detail: 'Live satellite detections' },
    { label: 'Critical Alerts', value: criticalAlerts.toLocaleString(), detail: 'Requires immediate action' },
    { label: 'High Alerts', value: highAlerts.toLocaleString(), detail: 'Escalated monitoring' },
    { label: 'Fire Clusters', value: clusterCount.toLocaleString(), detail: 'Spatial hotspots identified' },
  ];

  return (
    <div className="dashboard-page">
      <section className="dashboard-hero">
        <div className="dashboard-hero-copy">
          <span className="dashboard-kicker">Wildfire intelligence platform</span>
          <h1>Real-time forest fire detection and response in one command center.</h1>
          <p>
            Track NASA satellite detections, AI risk scores, live camera analysis, and emergency alerts from a
            single operational view built for continuous monitoring and real-world coordination.
          </p>
          <div className="dashboard-badges">
            <span className={`dashboard-chip ${socketStatus}`}>Live sync: {socketStatus}</span>
            <span className="dashboard-chip neutral">{updateLabel}</span>
            <span className="dashboard-chip neutral">{fireCount} detections</span>
            <span className="dashboard-chip neutral">{riskAssessments.length} risk regions</span>
          </div>
        </div>

        <div className="dashboard-hero-panel">
          {summaryCards.map((card) => (
            <div key={card.label} className="summary-card">
              <div className="summary-label">{card.label}</div>
              <div className="summary-value">{card.value}</div>
              <div className="summary-detail">{card.detail}</div>
            </div>
          ))}
          <div className="summary-card summary-card-wide">
            <div className="summary-label">Operational Snapshot</div>
            <div className="summary-detail">
              {analytics
                ? `Average confidence ${analytics.avg_confidence}% with ${analytics.avg_frp} MW average FRP.`
                : 'Loading the latest analytics snapshot.'}
            </div>
          </div>
        </div>
      </section>

      <div className="dashboard-layout">
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
              <AlertTriangle size={18} /> Alerts {alerts.length > 0 && `(${alerts.length})`}
            </button>
            <button
              className={`sidebar-tab ${activeTab === 'risk' ? 'active' : ''}`}
              onClick={() => setActiveTab('risk')}
            >
              <Activity size={18} /> AI Risk
            </button>
          </div>

          {activeTab === 'alerts' && <AlertsPanel alerts={alerts} />}
          {activeTab === 'risk' && (
            <RiskAnalysis riskAssessments={riskAssessments} clusters={clusters} />
          )}
        </div>
      </div>
    </div>
  );
}

function FullPageWrapper({ children }) {
  return <div className="full-page-content">{children}</div>;
}

function App() {
  const socketRef = useRef(null);
  const [socketInstance, setSocketInstance] = useState(null);
  const [fires, setFires] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [riskAssessments, setRiskAssessments] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isFetching, setIsFetching] = useState(false);
  const [socketStatus, setSocketStatus] = useState('connecting');
  const [notifications, setNotifications] = useState([]);
  const [voiceEnabled, setVoiceEnabled] = useState(() => {
    const persisted = window.localStorage.getItem('voice_alerts_enabled');
    return persisted ? persisted === 'true' : true;
  });

  const pushNotifications = useCallback((incoming) => {
    if (!incoming?.length) return;
    setNotifications((prev) => mergeNotifications(prev, incoming));
  }, []);

  const ingestAlerts = useCallback((incomingAlerts) => {
    const normalized = dedupeAlerts(incomingAlerts, 50);
    setAlerts(normalized);
    pushNotifications(normalized.filter((alert) => ['critical', 'high'].includes(alert.level)));
  }, [pushNotifications]);

  const toggleVoice = () => {
    setVoiceEnabled((prev) => {
      const next = !prev;
      window.localStorage.setItem('voice_alerts_enabled', String(next));
      return next;
    });
  };

  const testVoice = () => {
    if (!('speechSynthesis' in window)) return;
    const synth = window.speechSynthesis;

    // Clear any stuck / paused state (Chrome bug)
    if (synth.paused) synth.resume();
    synth.cancel();

    const doSpeak = () => {
      const u = new SpeechSynthesisUtterance(
        'Fire detected in Sector 5. Alert level HIGH. Please respond immediately.'
      );
      u.rate = 1.02;
      u.pitch = 1.0;
      u.volume = 1.0;

      const voices = synth.getVoices() || [];
      const preferred = voices.find(
        (v) => /en/i.test(v.lang) && /female|zira|aria|samantha|google.*us/i.test(v.name)
      );
      if (preferred) u.voice = preferred;
      else if (voices.length) u.voice = voices.find((v) => /en/i.test(v.lang)) || voices[0];

      synth.speak(u);
    };

    // Voices may not be loaded yet (Chrome loads them async)
    const voices = synth.getVoices() || [];
    if (voices.length > 0) {
      doSpeak();
    } else {
      const onReady = () => {
        synth.removeEventListener('voiceschanged', onReady);
        doSpeak();
      };
      synth.addEventListener('voiceschanged', onReady);
      // Fallback: speak anyway after 500ms even without voices
      setTimeout(() => {
        synth.removeEventListener('voiceschanged', onReady);
        doSpeak();
      }, 500);
    }
  };

  const fetchData = useCallback(async (retryCount = 0) => {
    setIsFetching(true);
    try {
      const results = await Promise.allSettled([
        fetch(`${API_BASE}/fires?limit=2000`),
        fetch(`${API_BASE}/analytics`),
        fetch(`${API_BASE}/risk-analysis`),
        fetch(`${API_BASE}/alerts?limit=30`),
      ]);

      const [firesRes, analyticsRes, riskRes, alertsRes] = results;

      if (firesRes.status === 'fulfilled' && firesRes.value.ok) {
        const data = await firesRes.value.json();
        setFires(data.fires || []);
        setLastUpdated(data.last_updated || null);
      }

      if (analyticsRes.status === 'fulfilled' && analyticsRes.value.ok) {
        const data = await analyticsRes.value.json();
        setAnalytics(data.analytics || null);
      }

      if (riskRes.status === 'fulfilled' && riskRes.value.ok) {
        const data = await riskRes.value.json();
        setRiskAssessments(data.risk_assessments || []);
        setClusters(data.clusters || []);
      }

      if (alertsRes.status === 'fulfilled' && alertsRes.value.ok) {
        const data = await alertsRes.value.json();
        ingestAlerts(data.alerts || []);
      }

      // If all requests failed and we have no data, retry after delay
      const allFailed = results.every(r => r.status === 'rejected' || (r.status === 'fulfilled' && !r.value.ok));
      if (allFailed && retryCount < 3) {
        console.warn(`[App] All API calls failed, retrying in 3s (attempt ${retryCount + 1}/3)...`);
        setTimeout(() => fetchData(retryCount + 1), 3000);
      }
    } catch (err) {
      console.error('Failed to fetch data:', err);
      if (retryCount < 3) {
        setTimeout(() => fetchData(retryCount + 1), 3000);
      }
    } finally {
      setIsFetching(false);
    }
  }, [ingestAlerts]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 300000);
    return () => clearInterval(interval);
  }, [fetchData]);

  useEffect(() => {
    const socket = io(SOCKET_BASE, {
      transports: ['polling', 'websocket'],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 15000,
    });

    socketRef.current = socket;
    setSocketInstance(socket);

    socket.on('connect', () => {
      console.log('[WS] Connected via', socket.io.engine?.transport?.name);
      setSocketStatus('connected');
    });

    socket.on('disconnect', (reason) => {
      console.log('[WS] Disconnected:', reason);
      setSocketStatus(reason === 'io server disconnect' ? 'offline' : 'connecting');
    });

    socket.on('connect_error', (err) => {
      console.warn('[WS] Connection error:', err.message);
      setSocketStatus((prev) => prev === 'connected' ? 'degraded' : 'connecting');
    });

    socket.on('fire_update', (payload) => {
      if (!payload) return;

      if (payload.fires) {
        setFires(payload.fires);
      }
      if (payload.analytics) {
        setAnalytics(payload.analytics);
      }
      if (payload.risk_assessments) {
        setRiskAssessments(payload.risk_assessments);
      }
      if (payload.clusters) {
        setClusters(payload.clusters);
      }
      if (payload.timestamp) {
        setLastUpdated(payload.timestamp);
      }
      if (payload.alerts) {
        ingestAlerts(payload.alerts);
      }
    });

    socket.on('dashboard_alert', (alert) => {
      const normalized = normalizeAlert(alert);
      if (!normalized) return;

      setAlerts((prev) => dedupeAlerts([normalized, ...prev], 50));
      if (['critical', 'high'].includes(normalized.level)) {
        pushNotifications([normalized]);
      }
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [ingestAlerts, pushNotifications]);

  useEffect(() => {
    const pollNotifications = async () => {
      try {
        const res = await fetch(`${API_BASE}/notifications`);
        if (!res.ok) return;
        const data = await res.json();
        const incoming = dedupeAlerts(data.notifications || [], 10);
        pushNotifications(incoming);
      } catch (err) {
        console.error('Notification poll failed', err);
      }
    };

    const timer = setInterval(pollNotifications, 5000);
    return () => clearInterval(timer);
  }, [pushNotifications]);

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
          socketStatus={socketStatus}
          onRefresh={fetchData}
          voiceEnabled={voiceEnabled}
          onToggleVoice={toggleVoice}
          onTestVoice={testVoice}
        />

        <Routes>
          <Route
            path="/"
            element={
              <DashboardShell
                fires={fires}
                analytics={analytics}
                alerts={alerts}
                riskAssessments={riskAssessments}
                clusters={clusters}
                socketStatus={socketStatus}
                lastUpdated={lastUpdated}
              />
            }
          />
          <Route path="/upload" element={<FullPageWrapper><ImageUpload socket={socketInstance} /></FullPageWrapper>} />
          <Route path="/history" element={<FullPageWrapper><FireHistory fires={fires} /></FullPageWrapper>} />
          <Route path="/regions" element={<FullPageWrapper><RegionSelector fires={fires} /></FullPageWrapper>} />
          <Route path="/visualizations" element={<FullPageWrapper><DataVisualization /></FullPageWrapper>} />
          <Route path="/live-feed" element={<FullPageWrapper><LiveCameraFeed /></FullPageWrapper>} />
          <Route path="/sensors" element={<FullPageWrapper><SensorMonitor /></FullPageWrapper>} />

          <Route path="/alert-center" element={<FullPageWrapper><AlertCenter /></FullPageWrapper>} />
          <Route path="/about" element={<FullPageWrapper><AboutPage /></FullPageWrapper>} />
        </Routes>

        <NotificationToast
          notifications={notifications}
          onDismiss={dismissNotification}
        />

        <VoiceToggleFAB
          voiceEnabled={voiceEnabled}
          onToggle={toggleVoice}
          onTest={testVoice}
        />

        <VoiceAssistant
          enabled={voiceEnabled}
          notifications={notifications}
          alerts={alerts}
          onUnsupported={() => setVoiceEnabled(false)}
        />
      </div>
    </BrowserRouter>
  );
}

export default App;
