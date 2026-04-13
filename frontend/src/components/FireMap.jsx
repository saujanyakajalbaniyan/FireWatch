import React, { useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import { AlertCircle } from 'lucide-react';
import { GoogleMap, MarkerF, useJsApiLoader } from '@react-google-maps/api';
import 'leaflet/dist/leaflet.css';

const severityColors = {
  critical: '#ef4444',
  high: '#f97316',
  moderate: '#f59e0b',
  low: '#22c55e',
};

const severityRadius = {
  critical: 12,
  high: 10,
  moderate: 8,
  low: 6,
};

function MapUpdater({ fires }) {
  useMap();
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
  const [viewMode, setViewMode] = useState('markers');
  const googleApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: googleApiKey || '',
  });

  const heatPoints = useMemo(() => {
    return fires.map((f) => ({
      ...f,
      heatWeight: Math.min(1, (f.frp || 0) / 120 + 0.08),
    }));
  }, [fires]);

  if (googleApiKey && isLoaded) {
    return (
      <div className="map-container">
        <div className="map-mode-toggle">
          <button className={`htab ${viewMode === 'markers' ? 'active' : ''}`} onClick={() => setViewMode('markers')}>Markers</button>
          <button className={`htab ${viewMode === 'heatmap' ? 'active' : ''}`} onClick={() => setViewMode('heatmap')}>Heatmap</button>
        </div>
        <GoogleMap
          mapContainerStyle={{ width: '100%', height: '100%' }}
          center={{ lat: 20, lng: 0 }}
          zoom={2}
          options={{
            disableDefaultUI: true,
            zoomControl: true,
            styles: [
              { elementType: 'geometry', stylers: [{ color: '#0f172a' }] },
              { elementType: 'labels.text.stroke', stylers: [{ color: '#0f172a' }] },
              { elementType: 'labels.text.fill', stylers: [{ color: '#64748b' }] },
            ],
          }}
        >
          {viewMode === 'markers' && fires.map((fire, idx) => (
            <MarkerF
              key={fire.id || idx}
              position={{ lat: fire.latitude, lng: fire.longitude }}
              title={`${fire.severity?.toUpperCase()} • FRP ${fire.frp} MW`}
              icon={{
                path: window.google.maps.SymbolPath.CIRCLE,
                fillColor: severityColors[fire.severity] || '#f59e0b',
                fillOpacity: 0.9,
                strokeColor: '#ffffff',
                strokeWeight: 1,
                scale: severityRadius[fire.severity] || 5,
              }}
            />
          ))}

          {viewMode === 'heatmap' && heatPoints.map((fire, idx) => (
            <MarkerF
              key={`heat_${fire.id || idx}`}
              position={{ lat: fire.latitude, lng: fire.longitude }}
              icon={{
                path: window.google.maps.SymbolPath.CIRCLE,
                fillColor: '#ef4444',
                fillOpacity: Math.max(0.1, fire.heatWeight * 0.7),
                strokeColor: '#f97316',
                strokeWeight: 0,
                scale: Math.max(6, Math.round(fire.heatWeight * 18)),
              }}
            />
          ))}
        </GoogleMap>
      </div>
    );
  }

  return (
    <div className="map-container">
      <div className="map-mode-toggle">
        <button className={`htab ${viewMode === 'markers' ? 'active' : ''}`} onClick={() => setViewMode('markers')}>Markers</button>
        <button className={`htab ${viewMode === 'heatmap' ? 'active' : ''}`} onClick={() => setViewMode('heatmap')}>Heatmap</button>
      </div>
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

        {(viewMode === 'markers' ? fires : heatPoints).map((fire, idx) => (
          <CircleMarker
            key={fire.id || idx}
            center={[fire.latitude, fire.longitude]}
            radius={viewMode === 'markers' ? (severityRadius[fire.severity] || 5) : Math.max(8, Math.round((fire.heatWeight || 0.2) * 20))}
            pathOptions={{
              fillColor: viewMode === 'markers' ? (severityColors[fire.severity] || '#f59e0b') : '#ef4444',
              fillOpacity: viewMode === 'markers' ? 0.8 : Math.max(0.12, (fire.heatWeight || 0.2) * 0.7),
              color: viewMode === 'markers' ? 'rgba(255,255,255,0.6)' : 'rgba(249,115,22,0.0)',
              weight: viewMode === 'markers' ? 2 : 0,
            }}
          >
            {viewMode === 'markers' && <Popup>
              <div>
                <div className="popup-title" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertCircle size={16} color={severityColors[fire.severity]} />
                  Fire Detection
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
            </Popup>}
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
