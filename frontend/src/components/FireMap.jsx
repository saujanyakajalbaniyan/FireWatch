import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const severityColors = {
  critical: '#ef4444',
  high: '#f97316',
  moderate: '#f59e0b',
  low: '#22c55e',
};

const severityRadius = {
  critical: 7,
  high: 6,
  moderate: 5,
  low: 4,
};

function MapUpdater({ fires }) {
  const map = useMap();
  const hasZoomed = useRef(false);

  useEffect(() => {
    if (fires.length > 0 && !hasZoomed.current) {
      // Don't auto-zoom — keep world view
      hasZoomed.current = true;
    }
  }, [fires]);

  return null;
}

export default function FireMap({ fires }) {
  return (
    <div className="map-container">
      <MapContainer
        center={[20, 0]}
        zoom={2}
        minZoom={2}
        maxZoom={14}
        style={{ width: '100%', height: '100%' }}
        zoomControl={true}
        attributionControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        />

        <MapUpdater fires={fires} />

        {fires.map((fire, idx) => (
          <CircleMarker
            key={fire.id || idx}
            center={[fire.latitude, fire.longitude]}
            radius={severityRadius[fire.severity] || 5}
            pathOptions={{
              fillColor: severityColors[fire.severity] || '#f59e0b',
              fillOpacity: 0.8,
              color: 'rgba(255,255,255,0.4)',
              weight: 1,
            }}
          >
            <Popup>
              <div>
                <div className="popup-title">
                  {fire.severity === 'critical' ? '🔴' :
                   fire.severity === 'high' ? '🟠' :
                   fire.severity === 'moderate' ? '🟡' : '🟢'}
                  {' '}Fire Detection
                </div>
                <div className="popup-row">
                  <span className="popup-label">Location</span>
                  <span className="popup-value">{fire.latitude?.toFixed(3)}, {fire.longitude?.toFixed(3)}</span>
                </div>
                <div className="popup-row">
                  <span className="popup-label">Confidence</span>
                  <span className="popup-value">{fire.confidence}%</span>
                </div>
                <div className="popup-row">
                  <span className="popup-label">FRP</span>
                  <span className="popup-value">{fire.frp} MW</span>
                </div>
                <div className="popup-row">
                  <span className="popup-label">Brightness</span>
                  <span className="popup-value">{fire.brightness} K</span>
                </div>
                <div className="popup-row">
                  <span className="popup-label">Satellite</span>
                  <span className="popup-value">{fire.satellite}</span>
                </div>
                <div className="popup-row">
                  <span className="popup-label">Time</span>
                  <span className="popup-value">{fire.acq_date} {fire.acq_time}</span>
                </div>
                <div className="popup-row">
                  <span className="popup-label">Severity</span>
                  <span className="popup-value" style={{ color: severityColors[fire.severity] }}>
                    {fire.severity?.toUpperCase()}
                  </span>
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
