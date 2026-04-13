import React, { useState, useRef, useEffect } from 'react';
import { Camera, UploadCloud, Folder, Search, Flame, CheckCircle, Maximize, Clock, AlertTriangle, Radio } from 'lucide-react';
import { API_BASE } from '../config';

export default function ImageUpload({ socket }) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!socket) return;

    const handleAutoScan = (data) => {
      if (data && data.analysis) {
        setResult(data.analysis);
        if (data.analysis.image_info?.thumbnail) {
          setPreview(data.analysis.image_info.thumbnail);
          setSelectedFile({ name: 'Live Auto-Scan Feed', size: 0 });
        }
      }
    };

    socket.on('auto_scan_update', handleAutoScan);
    return () => socket.off('auto_scan_update', handleAutoScan);
  }, [socket]);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      selectFile(file);
    }
  };

  const selectFile = (file) => {
    setSelectedFile(file);
    setResult(null);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target.result);
    reader.readAsDataURL(file);
  };

  const handleFileSelect = (e) => {
    if (e.target.files[0]) selectFile(e.target.files[0]);
  };

  const analyzeImage = async () => {
    if (!selectedFile) return;
    setIsAnalyzing(true);
    try {
      const formData = new FormData();
      formData.append('image', selectedFile);
      const res = await fetch(`${API_BASE}/upload-image`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error('Analysis failed:', err);
      setResult({ error: 'Failed to analyze image. Please try again.' });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const resetUpload = () => {
    setSelectedFile(null);
    setPreview(null);
    setResult(null);
  };

  const severityColor = {
    critical: 'var(--severity-critical)',
    high: 'var(--severity-high)',
    moderate: 'var(--severity-moderate)',
    low: 'var(--severity-low)',
  };

  return (
    <div className="upload-page">
      <div className="page-header">
        <h1 className="page-title"><Camera size={28} style={{marginRight: '8px'}} /> Live Footage Analysis</h1>
        <p className="page-subtitle">Real-time manual upload and automated background drone/satellite feed monitor</p>
      </div>

      <div className="upload-container">
        {/* Upload Zone */}
        <div className="upload-left">
          {!preview ? (
            <div
              className={`upload-dropzone ${isDragging ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="dropzone-icon"><UploadCloud size={48} /></div>
              <h3>Drop image here or click to browse</h3>
              <p>Supports JPG, PNG, WebP — Max 10MB</p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
            </div>
          ) : (
            <div className="upload-preview-area">
              <img src={preview} alt="Preview" className="upload-preview-img" />
              <div className="upload-file-info">
                <span><Folder size={16} style={{display:'inline', marginRight:'4px'}} /> {selectedFile?.name}</span>
                <span>{(selectedFile?.size / 1024).toFixed(1)} KB</span>
              </div>
              <div className="upload-actions">
                <button className="btn-analyze" onClick={analyzeImage} disabled={isAnalyzing}>
                  {isAnalyzing ? (
                    <>
                      <span className="btn-spinner"></span>
                      Analyzing...
                    </>
                  ) : (
                    <><Search size={16} style={{display:'inline', marginRight:'4px'}} /> Analyze for Fire</>
                  )}
                </button>
                <button className="btn-reset" onClick={resetUpload}>Clear</button>
              </div>
            </div>
          )}
        </div>

        {/* Results */}
        <div className="upload-right">
          {isAnalyzing && (
            <div className="analysis-loading">
              <div className="loading-spinner"></div>
              <h3>AI Analysis in Progress...</h3>
              <p>Scanning for fire patterns, smoke, and heat signatures</p>
            </div>
          )}

          {result && !result.error && (
            <div className="analysis-results">
              {/* Detection Badge */}
              <div className={`detection-badge ${result.fire_detected ? result.severity : 'safe'}`}>
                <div className="detection-icon">
                  {result.fire_detected ? <Flame size={24} /> : <CheckCircle size={24} />}
                </div>
                <div>
                  <h2>{result.fire_detected ? 'Fire Detected' : 'No Fire Detected'}</h2>
                  <p>Confidence: {result.confidence}%</p>
                </div>
                {result.fire_detected && (
                  <span className="severity-tag" style={{ background: severityColor[result.severity] }}>
                    {result.severity?.toUpperCase()}
                  </span>
                )}
              </div>

              {/* Score Breakdown */}
              <div className="scores-grid">
                {Object.entries(result.scores || {}).map(([key, val]) => (
                  <div key={key} className="score-item">
                    <div className="score-bar-bg">
                      <div
                        className="score-bar-fill"
                        style={{
                          width: `${val}%`,
                          background: val > 60 ? 'var(--severity-critical)' :
                            val > 35 ? 'var(--fire-orange)' : 'var(--severity-low)',
                        }}
                      ></div>
                    </div>
                    <div className="score-info">
                      <span className="score-label">{key.replace('_', ' ')}</span>
                      <span className="score-value">{val}%</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Recommendations */}
              {result.recommendations && result.recommendations.length > 0 && (
                <div className="recommendations">
                  <h3>Recommendations</h3>
                  {result.recommendations.map((rec, i) => (
                    <div key={i} className={`rec-card ${rec.type}`}>
                      <strong>{rec.title}</strong>
                      <p>{rec.message}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Image Info */}
              <div className="image-meta">
                <span><Maximize size={16} style={{display:'inline', marginRight:'4px'}} /> {result.image_info?.width} × {result.image_info?.height}px</span>
                <span><Clock size={16} style={{display:'inline', marginRight:'4px'}} /> {new Date(result.analysis_time).toLocaleString()}</span>
              </div>
            </div>
          )}

          {result?.error && (
            <div className="analysis-error">
              <div className="empty-state-icon"><AlertTriangle size={32} /></div>
              <p>{result.error}</p>
            </div>
          )}

          {!result && !isAnalyzing && (
            <div className="analysis-placeholder">
              <div className="empty-state-icon"><Radio size={32} /></div>
              <h3>Waiting for live feed...</h3>
              <p>The AI auto-scanner will stream a new image here momentarily, or you can manually upload one.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
