import React, { useCallback, useEffect, useState } from 'react';
import { API_BASE } from '../config';

function StatusBadge({ enabled, configured }) {
  const label = enabled ? 'Live' : configured ? 'Configured' : 'Not configured';
  const className = enabled ? 'status-chip low' : configured ? 'status-chip moderate' : 'status-chip high';
  return <span className={className}>{label}</span>;
}

export default function AlertCenter() {
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sendingTest, setSendingTest] = useState(false);
  const [channelStatus, setChannelStatus] = useState(null);

  const [email, setEmail] = useState({
    smtp_server: 'smtp.gmail.com',
    smtp_port: 587,
    sender_email: '',
    sender_password: '',
    recipient_email: '',
  });

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

  const loadChannelStatus = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/alerts/channels`);
      if (!res.ok) return;
      const data = await res.json();
      setChannelStatus(data);

      if (data.email?.config) {
        setEmail((prev) => ({
          ...prev,
          smtp_server: data.email.config.smtp_server || prev.smtp_server,
          smtp_port: data.email.config.smtp_port || prev.smtp_port,
          sender_email: data.email.config.sender_email || prev.sender_email,
          recipient_email: data.email.config.recipient_email || prev.recipient_email,
        }));
      }
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
      setMessage('Unable to load alert channel status.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadChannelStatus();
  }, [loadChannelStatus]);

  const postConfig = async (path, body) => {
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setMessage(`${path} -> ${data.status || data.error || 'updated'}`);
      await loadChannelStatus();
    } catch (err) {
      console.error('Channel update failed:', err);
      setMessage(`${path} -> request failed`);
    }
  };

  const sendTestAlert = async () => {
    setSendingTest(true);
    try {
      const res = await fetch(`${API_BASE}/alerts/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Real-time alert channel test',
          message: 'This is a real-time delivery test for email, SMS, and mobile channels.',
        }),
      });
      const data = await res.json();
      const channels = data.alert?.dispatch?.channels;
      if (channels) {
        const summary = Object.entries(channels).map(([key, value]) => `${key}: ${value.status}`).join(', ');
        setMessage(`Test alert sent -> ${summary}`);
      } else {
        setMessage('Test alert sent.');
      }
    } catch (err) {
      console.error('Test alert failed:', err);
      setMessage('Test alert failed.');
    } finally {
      setSendingTest(false);
    }
  };

  return (
    <div className="alerts-config-page">
      <div className="page-header">
        <h1 className="page-title">Alert Center</h1>
        <p className="page-subtitle">Configure and test real-time email, SMS, and mobile alert delivery.</p>
      </div>

      <div className="alerts-config-grid">
        <section className="config-card">
          <div className="config-card-head">
            <h3>Email Alerts</h3>
            <StatusBadge enabled={channelStatus?.email?.enabled} configured={channelStatus?.email?.configured} />
          </div>
          <input placeholder="SMTP server" value={email.smtp_server} onChange={(e) => setEmail((p) => ({ ...p, smtp_server: e.target.value }))} />
          <input placeholder="SMTP port" type="number" value={email.smtp_port} onChange={(e) => setEmail((p) => ({ ...p, smtp_port: Number(e.target.value) }))} />
          <input placeholder="Sender email" value={email.sender_email} onChange={(e) => setEmail((p) => ({ ...p, sender_email: e.target.value }))} />
          <input placeholder="App password" type="password" value={email.sender_password} onChange={(e) => setEmail((p) => ({ ...p, sender_password: e.target.value }))} />
          <input placeholder="Recipient email" value={email.recipient_email} onChange={(e) => setEmail((p) => ({ ...p, recipient_email: e.target.value }))} />
          <button className="btn-analyze" onClick={() => postConfig('/alerts/email', email)}>Save Email Config</button>
        </section>

        <section className="config-card">
          <div className="config-card-head">
            <h3>SMS Alerts</h3>
            <StatusBadge enabled={channelStatus?.sms?.enabled} configured={channelStatus?.sms?.configured} />
          </div>
          <input placeholder="Account SID" value={sms.account_sid} onChange={(e) => setSms((p) => ({ ...p, account_sid: e.target.value }))} />
          <input placeholder="Auth Token" type="password" value={sms.auth_token} onChange={(e) => setSms((p) => ({ ...p, auth_token: e.target.value }))} />
          <input placeholder="From Number" value={sms.from_number} onChange={(e) => setSms((p) => ({ ...p, from_number: e.target.value }))} />
          <input placeholder="To Number" value={sms.to_number} onChange={(e) => setSms((p) => ({ ...p, to_number: e.target.value }))} />
          <button className="btn-analyze" onClick={() => postConfig('/alerts/sms', sms)}>Save SMS Config</button>
        </section>

        <section className="config-card">
          <div className="config-card-head">
            <h3>Mobile Push</h3>
            <StatusBadge enabled={channelStatus?.mobile?.enabled} configured={channelStatus?.mobile?.configured} />
          </div>
          <input placeholder="Webhook URL" value={mobile.webhook_url} onChange={(e) => setMobile((p) => ({ ...p, webhook_url: e.target.value }))} />
          <input placeholder="API key (optional)" value={mobile.api_key} onChange={(e) => setMobile((p) => ({ ...p, api_key: e.target.value }))} />
          <button className="btn-analyze" onClick={() => postConfig('/alerts/mobile', mobile)}>Save Mobile Config</button>
        </section>
      </div>

      <div className="config-toolbar">
        <button className="btn-analyze" onClick={sendTestAlert} disabled={sendingTest || loading}>
          {sendingTest ? 'Sending test...' : 'Send Real-Time Test Alert'}
        </button>
        <button className="btn-reset" onClick={loadChannelStatus} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh Status'}
        </button>
      </div>

      {message && <p className="config-message">{message}</p>}
    </div>
  );
}
