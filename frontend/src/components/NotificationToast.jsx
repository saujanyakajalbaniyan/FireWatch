import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';

export default function NotificationToast({ notifications, onDismiss }) {
  return (
    <div className="toast-container">
      {notifications.map(notif => (
        <Toast key={notif.id} notification={notif} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

function Toast({ notification, onDismiss }) {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsExiting(true);
      setTimeout(() => onDismiss(notification.id), 300);
    }, 6000);
    return () => clearTimeout(timer);
  }, [notification.id, onDismiss]);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(() => onDismiss(notification.id), 300);
  };

  const levelColor = {
    critical: 'var(--severity-critical)',
    high: 'var(--severity-high)',
    moderate: 'var(--severity-moderate)',
    low: 'var(--severity-low)',
  };

  return (
    <div className={`toast ${isExiting ? 'exit' : 'enter'}`}
         style={{ borderLeftColor: levelColor[notification.level] || levelColor.high }}>
      <div className="toast-content">
        <div className="toast-pulse" style={{ background: levelColor[notification.level] }}></div>
        <div className="toast-text">
          <strong>{notification.title}</strong>
          <p>{notification.message?.slice(0, 100)}</p>
        </div>
        <button className="toast-close" onClick={handleDismiss}><X size={16} /></button>
      </div>
    </div>
  );
}
