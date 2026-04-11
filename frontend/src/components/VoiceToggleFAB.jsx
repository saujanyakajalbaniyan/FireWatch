import React, { useState } from 'react';

export default function VoiceToggleFAB({ voiceEnabled, onToggle, onTest }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`voice-fab-wrapper ${expanded ? 'expanded' : ''}`}>
      {/* Expanded panel */}
      {expanded && (
        <div className="voice-fab-panel">
          <div className="voice-fab-panel-header">
            <span className="voice-fab-panel-title">Voice Alerts</span>
            <button className="voice-fab-close" onClick={() => setExpanded(false)}>✕</button>
          </div>

          <p className="voice-fab-desc">
            {voiceEnabled
              ? 'Voice alerts are active. Critical & high alerts will be spoken aloud.'
              : 'Voice alerts are muted. Enable to hear spoken fire alerts.'}
          </p>

          <button className={`voice-fab-toggle-btn ${voiceEnabled ? 'on' : 'off'}`} onClick={onToggle}>
            <span className="voice-fab-toggle-icon">{voiceEnabled ? '🎤' : '🔇'}</span>
            <span>{voiceEnabled ? 'Disable Voice Alerts' : 'Enable Voice Alerts'}</span>
          </button>

          <button className="voice-fab-test-btn" onClick={onTest}>
            🔊 Test Voice
          </button>
        </div>
      )}

      {/* FAB button */}
      <button
        className={`voice-fab ${voiceEnabled ? 'on' : 'off'}`}
        onClick={() => setExpanded((prev) => !prev)}
        title={voiceEnabled ? 'Voice alerts ON — click to manage' : 'Voice alerts OFF — click to manage'}
      >
        <span className="voice-fab-icon">{voiceEnabled ? '🎤' : '🔇'}</span>
        {voiceEnabled && <span className="voice-fab-pulse"></span>}
      </button>
    </div>
  );
}
