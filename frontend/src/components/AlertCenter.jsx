import React, { useCallback, useEffect, useState } from 'react';
import { API_BASE } from '../config';
import {
  MessageSquare, Smartphone, Send, RefreshCw, CheckCircle, XCircle,
  AlertTriangle, Info, BellRing, ExternalLink,
} from 'lucide-react';

function StatusBadge({ enabled, configured }) {
  if (enabled) return <span className="status-chip low"><CheckCircle size={12} /> Live</span>;
  if (configured) return <span className="status-chip moderate"><AlertTriangle size={12} /> Configured</span>;
  return <span className="status-chip high"><XCircle size={12} /> Not configured</span>;
}

export default function AlertCenter() {
  const [message, setMessage] = useState('');
  const [msgType, setMsgType] = useState('info'); // 'info' | 'success' | 'error'
  const [loading, setLoading] = useState(true);
  const [sendingTest, setSendingTest] = useState(false);
  const [sendingSmsTest, setSendingSmsTest] = useState(false);
  const [savingSms, setSavingSms] = useState(false);
  const [channelStatus, setChannelStatus] = useState(null);

  const [sms, setSms] = useState({
    account_sid: '',
    auth_token: '',
    from_number: '',
    to_number: '',
  });

  const [mobile, setMobile] = useState({
    webhook_url: '',
    api_key: '',
  });

  const showMsg = (text, type = 'info') => {
    setMessage(text);
    setMsgType(type);
    // Auto-clear after 10s
    setTimeout(() => setMessage(''), 10000);
  };

  const loadChannelStatus = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/alerts/channels`);
      if (!res.ok) return;
      const data = await res.json();
      setChannelStatus(data);

      if (data.sms?.config) {
        setSms((prev) => ({
          ...prev,
          account_sid: data.sms.config.account_sid || prev.account_sid,
          from_number: data.sms.config.from_number || prev.from_number,
          to_number: data.sms.config.to_number || prev.to_number,
        }));
      }
      if (data.mobile?.config) {
        setMobile((prev) => ({
          ...prev,
          webhook_url: data.mobile.config.webhook_url || prev.webhook_url,
          api_key: data.mobile.config.api_key || prev.api_key,
        }));
      }
    } catch (err) {
      console.error('Failed to load alert status:', err);
      showMsg('Unable to load alert channel status.', 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadChannelStatus();
  }, [loadChannelStatus]);

  /* ─── Save SMS Config ─── */
  const saveSmsConfig = async () => {
    setSavingSms(true);
    try {
      const res = await fetch(`${API_BASE}/alerts/sms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sms),
      });
      const data = await res.json();
      if (data.status === 'configured') {
        showMsg(`SMS configured! Alerts will be sent to ${data.to_number}`, 'success');
      } else {
        showMsg(`SMS config incomplete — please fill all 4 fields.`, 'error');
      }
      await loadChannelStatus();
    } catch (err) {
      console.error('SMS save failed:', err);
      showMsg('Failed to save SMS config.', 'error');
    } finally {
      setSavingSms(false);
    }
  };

  /* ─── Save Mobile Config ─── */
  const saveMobileConfig = async () => {
    try {
      const res = await fetch(`${API_BASE}/alerts/mobile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mobile),
      });
      const data = await res.json();
      showMsg(`Mobile config: ${data.status || 'updated'}`, data.status === 'configured' ? 'success' : 'info');
      await loadChannelStatus();
    } catch (err) {
      console.error('Mobile config failed:', err);
      showMsg('Failed to save mobile config.', 'error');
    }
  };

  /* ─── Send Test SMS (direct, bypasses cooldown) ─── */
  const sendTestSms = async () => {
    setSendingSmsTest(true);
    try {
      const res = await fetch(`${API_BASE}/alerts/sms/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await res.json();
      if (data.status === 'sent') {
        showMsg(`SMS sent successfully to ${data.to}! Check your phone.`, 'success');
      } else {
        showMsg(`SMS failed: ${data.error || 'Unknown error'}`, 'error');
      }
    } catch (err) {
      console.error('Test SMS failed:', err);
      showMsg('Test SMS request failed — is the backend running?', 'error');
    } finally {
      setSendingSmsTest(false);
    }
  };

  /* ─── Send Full Test Alert (all channels) ─── */
  const sendTestAlert = async () => {
    setSendingTest(true);
    try {
      const res = await fetch(`${API_BASE}/alerts/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Real-time alert channel test',
          message: 'This is a real-time delivery test for SMS and mobile channels.',
        }),
      });
      const data = await res.json();
      const channels = data.alert?.dispatch?.channels;
      if (channels) {
        const summary = Object.entries(channels)
          .map(([key, val]) => `${key}: ${val.status}${val.reason ? ` (${val.reason})` : ''}`)
          .join(' | ');
        showMsg(`Test alert dispatched — ${summary}`, 'success');
      } else {
        showMsg('Test alert sent to dashboard.', 'info');
      }
    } catch (err) {
      console.error('Test alert failed:', err);
      showMsg('Test alert failed — is the backend running?', 'error');
    } finally {
      setSendingTest(false);
    }
  };

  return (
    <div className="alerts-config-page">
      <div className="page-header">
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', margin: 0 }}>
          <BellRing size={28} style={{ marginRight: '8px' }} /> Alert Center
        </h1>
        <p className="page-subtitle">Configure and test real-time SMS and mobile alert delivery.</p>
      </div>

      <div className="alerts-config-grid">
        {/* SMS Config Card */}
        <section className="config-card">
          <div className="config-card-head">
            <h3 style={{ display: 'flex', alignItems: 'center', margin: 0 }}><MessageSquare size={18} style={{ marginRight: '6px' }} /> SMS Alerts (Twilio)</h3>
            <StatusBadge enabled={channelStatus?.sms?.enabled} configured={channelStatus?.sms?.configured} />
          </div>
          <input
            placeholder="Account SID (e.g. ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)"
            value={sms.account_sid}
            onChange={(e) => setSms((p) => ({ ...p, account_sid: e.target.value }))}
          />
          <input
            placeholder="Auth Token"
            type="password"
            value={sms.auth_token}
            onChange={(e) => setSms((p) => ({ ...p, auth_token: e.target.value }))}
          />
          <input
            placeholder="From Number (e.g. +1234567890)"
            value={sms.from_number}
            onChange={(e) => setSms((p) => ({ ...p, from_number: e.target.value }))}
          />
          <input
            placeholder="To Number — your phone (e.g. +919876543210)"
            value={sms.to_number}
            onChange={(e) => setSms((p) => ({ ...p, to_number: e.target.value }))}
            style={{ borderColor: sms.to_number ? 'var(--severity-low)' : undefined }}
          />
          <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
            <button className="btn-analyze" onClick={saveSmsConfig} disabled={savingSms}>
              {savingSms ? 'Saving...' : 'Save SMS Config'}
            </button>
            <button
              className="btn-analyze"
              onClick={sendTestSms}
              disabled={sendingSmsTest || !channelStatus?.sms?.enabled}
              style={{ background: channelStatus?.sms?.enabled ? 'var(--severity-low)' : undefined }}
            >
              <Send size={14} style={{ marginRight: '4px' }} />
              {sendingSmsTest ? 'Sending...' : 'Send Test SMS'}
            </button>
          </div>
        </section>

        {/* Mobile Push Card */}
        <section className="config-card">
          <div className="config-card-head">
            <h3 style={{ display: 'flex', alignItems: 'center', margin: 0 }}><Smartphone size={18} style={{ marginRight: '6px' }} /> Mobile Push</h3>
            <StatusBadge enabled={channelStatus?.mobile?.enabled} configured={channelStatus?.mobile?.configured} />
          </div>
          <input
            placeholder="Webhook URL"
            value={mobile.webhook_url}
            onChange={(e) => setMobile((p) => ({ ...p, webhook_url: e.target.value }))}
          />
          <input
            placeholder="API key (optional)"
            value={mobile.api_key}
            onChange={(e) => setMobile((p) => ({ ...p, api_key: e.target.value }))}
          />

          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '8px', fontSize: '12px', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)', lineHeight: '1.5', flex: 1 }}>
            <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '6px' }}>How to use this feature:</strong>
            Connect your custom apps, <strong>Slack</strong>, <strong>Discord</strong>, or <strong>Zapier</strong>. We will send an instant JSON payload with the fire's coordinates and severity rating directly to this webhook when detected.
          </div>
          <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
            <button className="btn-analyze" onClick={saveMobileConfig}>Save Mobile Config</button>
          </div>
        </section>

        {/* Dispatch Rules Card (Fills 3rd Column) */}
        <section className="config-card">
          <div className="config-card-head">
            <h3 style={{ display: 'flex', alignItems: 'center', margin: 0 }}><Info size={18} style={{ marginRight: '6px' }} /> Dispatch Rules & Info</h3>
          </div>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '12px', color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.5', marginTop: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
              <CheckCircle size={14} style={{ color: 'var(--severity-low)', marginTop: '3px', flexShrink: 0 }} />
              <span><strong>Severity Filter:</strong> Alerts are only dispatched for <strong>High</strong> or <strong>Critical</strong> severity fire detections. Minor anomalies are logged but do not trigger SMS.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
              <AlertTriangle size={14} style={{ color: 'var(--fire-orange)', marginTop: '3px', flexShrink: 0 }} />
              <span><strong>Global Cooldown:</strong> To conserve your Twilio quota and prevent spam, SMS alerts have a <strong>30-minute global cooldown</strong> after a successful dispatch.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
              <Smartphone size={14} style={{ color: 'var(--text-primary)', marginTop: '3px', flexShrink: 0 }} />
              <span><strong>Bypassing Cooldown:</strong> Webhook / Mobile Push notifications send instantly upon detection and completely bypass the SMS cooldown limitation.</span>
            </div>
          </div>
        </section>
      </div>

      {/* Global Test */}
      <div className="config-toolbar">
        <button className="btn-analyze" onClick={sendTestAlert} disabled={sendingTest || loading}>
          {sendingTest ? 'Sending test...' : 'Send Full Channel Test'}
        </button>
        <button className="btn-reset" onClick={loadChannelStatus} disabled={loading}>
          <RefreshCw size={14} style={{ marginRight: '4px' }} />
          {loading ? 'Refreshing...' : 'Refresh Status'}
        </button>
      </div>

      {/* Status Message */}
      {message && (
        <p className={`config-message ${msgType}`} style={{
          padding: '12px 16px',
          borderRadius: '8px',
          marginTop: '16px',
          background: msgType === 'success' ? 'rgba(34,197,94,0.15)' :
                      msgType === 'error' ? 'rgba(239,68,68,0.15)' : 'rgba(59,130,246,0.15)',
          borderLeft: `3px solid ${
            msgType === 'success' ? 'var(--severity-low)' :
            msgType === 'error' ? 'var(--severity-critical)' : 'var(--fire-orange)'
          }`,
          color: 'var(--text-primary)',
        }}>
          {msgType === 'success' && <CheckCircle size={14} style={{ display: 'inline', marginRight: '6px' }} />}
          {msgType === 'error' && <XCircle size={14} style={{ display: 'inline', marginRight: '6px' }} />}
          {msgType === 'info' && <Info size={14} style={{ display: 'inline', marginRight: '6px' }} />}
          {message}
        </p>
      )}
    </div>
  );
}
