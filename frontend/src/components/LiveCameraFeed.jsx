import React, { useCallback, useEffect, useRef, useState } from 'react';
import { API_BASE } from '../config';

export default function LiveCameraFeed() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const isAnalyzingRef = useRef(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const analyzeCurrentFrame = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || isAnalyzingRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);

    isAnalyzingRef.current = true;
    setIsAnalyzing(true);
    try {
      const res = await fetch(`${API_BASE}/live-feed/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ frame: dataUrl }),
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      isAnalyzingRef.current = false;
      setIsAnalyzing(false);
    }
  }, []);

  useEffect(() => {
    let intervalId;
    if (isRunning) {
      intervalId = setInterval(() => {
        analyzeCurrentFrame();
      }, 5000);
    }
    return () => clearInterval(intervalId);
  }, [isRunning, analyzeCurrentFrame]);

  const startCamera = async () => {
    try {
      setError('');
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsRunning(true);
    } catch (err) {
      setError('Camera access failed. Allow webcam permission and retry.');
      console.error(err);
    }
  };

  const stopCamera = () => {
    const stream = streamRef.current || videoRef.current?.srcObject;
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsRunning(false);
  };

  useEffect(() => {
    const videoEl = videoRef.current;
    return () => {
      const stream = streamRef.current || videoEl?.srcObject;
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const overlayRegions = result?.regions_of_interest || [];

  return (
    <div className="live-feed-page">
      <div className="page-header">
        <h1 className="page-title">Live Camera Feed</h1>
        <p className="page-subtitle">Real-time frame analysis with fire detection overlay every 5 seconds</p>
      </div>

      <div className="live-feed-layout">
        <div className="live-feed-stage">
          <div className="video-shell">
            <video ref={videoRef} autoPlay playsInline muted className="live-video" />
            <canvas ref={canvasRef} className="live-canvas" />
            <div className="overlay-layer">
              {overlayRegions.map((region, index) => (
                <div
                  key={index}
                  className="fire-overlay-box"
                  style={{
                    left: `${region.x}%`,
                    top: `${region.y}%`,
                    width: `${region.width}%`,
                    height: `${region.height}%`,
                  }}
                >
                  <span>{region.density}%</span>
                </div>
              ))}
            </div>
          </div>

          <div className="live-controls">
            {!isRunning ? (
              <button className="btn-analyze" onClick={startCamera}>Start Camera</button>
            ) : (
              <>
                <button className="btn-analyze" onClick={analyzeCurrentFrame} disabled={isAnalyzing}>
                  {isAnalyzing ? 'Analyzing...' : 'Analyze Now'}
                </button>
                <button className="btn-reset" onClick={stopCamera}>Stop</button>
              </>
            )}
          </div>

          {error && <p className="helper-error">{error}</p>}
        </div>

        <div className="live-feed-sidebar">
          <div className="metric-card">
            <h3>Detection Status</h3>
            <p className={`status-chip ${result?.fire_detected ? 'critical' : 'safe'}`}>
              {result ? (result.fire_detected ? 'Fire detected' : 'No fire detected') : 'Waiting for analysis'}
            </p>
          </div>
          <div className="metric-card">
            <h3>Scene Classification</h3>
            <p>{result?.scene_classification || 'unknown'}</p>
          </div>
          <div className="metric-card">
            <h3>Confidence</h3>
            <p>{result?.confidence ?? 0}%</p>
          </div>
          <div className="metric-card">
            <h3>Alert Dispatch</h3>
            <p>
              {result?.alert_dispatch
                ? `${result.alert_dispatch.latency_ms}ms (${result.alert_dispatch.within_5_seconds ? 'within 5s' : 'over 5s'})`
                : 'No alert dispatched'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
