import React, { useRef, useState } from 'react';
import { UploadCloud } from 'lucide-react';

export default function VideoUploader({ onFileSelect }) {
  const fileInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file) => {
    if (!file.type.startsWith('video/')) {
      alert('Please upload a valid video file.');
      return;
    }
    onFileSelect(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div 
      className={`uploader glass-panel ${isDragging ? 'dragging' : ''}`}
      style={{ 
        border: isDragging ? '2px dashed #a855f7' : '2px dashed rgba(255,255,255,0.1)',
        transition: 'all 0.2s',
        cursor: 'pointer'
      }}
      onClick={() => fileInputRef.current?.click()}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input 
        type="file" 
        accept="video/*" 
        style={{ display: 'none' }} 
        ref={fileInputRef}
        onChange={handleChange}
      />
      <div>
        <UploadCloud className="upload-icon" size={48} style={{ color: isDragging ? '#a855f7' : 'inherit' }} />
        <h3>Upload Video for Analysis</h3>
        <p className="subtitle" style={{ marginTop: '0.5rem' }}>Drag & drop or click to browse</p>
      </div>
    </div>
  );
}
