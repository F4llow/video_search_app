import React, { useState, useEffect } from 'react';
import VideoUploader from '../components/VideoUploader';
import VideoPlayer from '../components/VideoPlayer';

export default function AnalyzePage() {
  const [currentVideoUrl, setCurrentVideoUrl] = useState(null); // Local blob URL for preview
  const [selectedFile, setSelectedFile] = useState(null);
  
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatusMsg, setUploadStatusMsg] = useState("");
  const [uploadedFilename, setUploadedFilename] = useState(null);
  const [processingStatus, setProcessingStatus] = useState(""); // "", "queued", "processing", "completed", "failed"
  const [startTime, setStartTime] = useState(null);
  const [elapsedSecs, setElapsedSecs] = useState(0);
  const [summary, setSummary] = useState("");

  const handleFileSelect = (file) => {
    const blobUrl = URL.createObjectURL(file);
    setCurrentVideoUrl(blobUrl);
    setSelectedFile(file);
    setUploadStatusMsg("");
    setUploadedFilename(null);
    setProcessingStatus("");
    setStartTime(null);
    setElapsedSecs(0);
    setSummary("");
  };

  const handleAnalyze = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setUploadStatusMsg("Uploading to server...");
    
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      
      setUploadedFilename(data.filename);
      setProcessingStatus("queued");
      setUploadStatusMsg("Queued for processing. Waiting for Omni model...");
      setStartTime(Date.now());
      setElapsedSecs(0);
    } catch (err) {
      setUploadStatusMsg(`❌ Upload Error: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };
  
  const handleCancel = async () => {
    if (uploadedFilename && (processingStatus === "queued" || processingStatus === "processing")) {
      try {
        await fetch(`http://localhost:8000/cancel/${uploadedFilename}`, { method: 'POST' });
      } catch (e) { console.error(e); }
    }
    // Reset state
    setCurrentVideoUrl(null);
    setSelectedFile(null);
    setUploadStatusMsg("");
    setUploadedFilename(null);
    setProcessingStatus("");
    setStartTime(null);
    setElapsedSecs(0);
    setSummary("");
  };

  // Timer logic
  useEffect(() => {
    let timer;
    if ((processingStatus === "processing" || processingStatus === "queued") && startTime) {
      timer = setInterval(() => {
        setElapsedSecs(Math.floor((Date.now() - startTime) / 1000));
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [processingStatus, startTime]);

  // Polling logic
  useEffect(() => {
    let interval;
    if (uploadedFilename && (processingStatus === "processing" || processingStatus === "queued")) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`http://localhost:8000/status/${uploadedFilename}`);
          const data = await res.json();
          if (data.status === "completed") {
            setProcessingStatus("completed");
            setSummary(data.summary);
          } else if (data.status === "failed") {
            setProcessingStatus("failed");
            setUploadStatusMsg("❌ Processing failed. Please try another video.");
          } else if (data.status === "processing") {
            setProcessingStatus("processing");
            setUploadStatusMsg("The Omni model is analyzing your video...");
          }
        } catch(e) {
          console.error("Status polling error", e);
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [uploadedFilename, processingStatus]);

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      {!currentVideoUrl ? (
        <VideoUploader onFileSelect={handleFileSelect} />
      ) : (
        <div className="glass-panel">
          <VideoPlayer url={currentVideoUrl} />
          
          {processingStatus === "" && !isUploading && (
            <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
              <button className="btn" style={{ flex: 1, background: 'var(--surface-color)', border: '1px solid rgba(255,255,255,0.1)' }} onClick={handleCancel}>
                Cancel
              </button>
              <button className="btn" style={{ flex: 2 }} onClick={handleAnalyze}>
                Analyze Video
              </button>
            </div>
          )}

          {isUploading && (
            <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
              <div className="spinner"></div>
              <p style={{ color: 'var(--text-secondary)', marginTop: '1rem' }}>{uploadStatusMsg}</p>
            </div>
          )}

          {(processingStatus === "queued" || processingStatus === "processing") && (
            <div style={{ marginTop: '1.5rem', marginBottom: '1rem' }}>
              <p style={{ color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.9rem' }}>
                <span>{uploadStatusMsg}</span>
                <span style={{ fontWeight: 'bold', color: '#a855f7', background: 'rgba(168, 85, 247, 0.1)', padding: '4px 8px', borderRadius: '4px' }}>
                  {formatTime(elapsedSecs)}
                </span>
              </p>
              <div className="progress-container">
                <div className="progress-bar-fill"></div>
              </div>
              <button className="btn" style={{ width: '100%', marginTop: '1rem', background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: '1px solid #ef4444' }} onClick={handleCancel}>
                Cancel Processing
              </button>
            </div>
          )}

          {processingStatus === "completed" && (
            <div style={{ marginTop: '1.5rem' }}>
              <div className="status-completed">
                ✅ Processing complete in {formatTime(elapsedSecs)}!
              </div>
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', marginTop: '1rem' }}>
                <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem' }}>AI Summary</h3>
                <div style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', lineHeight: '1.6', fontSize: '0.95rem' }}>
                  {summary}
                </div>
              </div>
              <button className="btn" style={{ width: '100%', marginTop: '1.5rem' }} onClick={handleCancel}>
                Analyze Another Video
              </button>
            </div>
          )}

          {processingStatus === "failed" && (
            <div style={{ marginTop: '1.5rem' }}>
              <div style={{ color: '#ef4444', textAlign: 'center', padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px' }}>
                {uploadStatusMsg}
              </div>
              <button className="btn" style={{ width: '100%', marginTop: '1rem' }} onClick={handleCancel}>
                Try Again
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
