import React, { useState, useRef } from 'react';

const API_BASE = 'http://localhost:5000/api';

export default function ImageUpload() {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const fileInputRef = useRef(null);

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
        <h1 className="page-title">📸 Image Fire Detection</h1>
        <p className="page-subtitle">Upload an image to analyze it for fire and smoke using AI</p>
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
              <div className="dropzone-icon">📤</div>
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
                <span>📁 {selectedFile?.name}</span>
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
                    '🔍 Analyze for Fire'
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
                  {result.fire_detected ? '🔥' : '✅'}
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
                <span>📐 {result.image_info?.width} × {result.image_info?.height}px</span>
                <span>⏱️ {new Date(result.analysis_time).toLocaleString()}</span>
              </div>
            </div>
          )}

          {result?.error && (
            <div className="analysis-error">
              <div className="empty-state-icon">⚠️</div>
              <p>{result.error}</p>
            </div>
          )}

          {!result && !isAnalyzing && (
            <div className="analysis-placeholder">
              <div className="empty-state-icon">🔍</div>
              <h3>Upload an image to begin</h3>
              <p>Our AI will analyze the image for fire, smoke, and heat signatures</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
