import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Upload, File as FileIcon, Loader, FolderOpen, Clock, Trash2 } from 'lucide-react';

const FileUpload = ({ onUploadSuccess, activeMedia }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [recentFiles, setRecentFiles] = useState([]);
  const fileInputRef = useRef(null);

  const fetchRecentFiles = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await axios.get(`${apiUrl}/api/documents/`);
      // Show latest files first
      setRecentFiles(response.data.reverse());
    } catch (error) {
      console.error('Failed to fetch recent files', error);
    }
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      await axios.delete(`${apiUrl}/api/documents/${id}/`);
      fetchRecentFiles(); // Refresh the list
    } catch (error) {
      console.error('Failed to delete file', error);
      alert('Failed to delete file');
    }
  };

  useEffect(() => {
    fetchRecentFiles();
  }, []);

  const LARGE_FILE_THRESHOLD = 25 * 1024 * 1024; // 25 MB

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', file.name);

    let fileType = 'other';
    if (file.type.includes('pdf')) fileType = 'pdf';
    if (file.type.includes('audio')) fileType = 'audio';
    if (file.type.includes('video')) fileType = 'video';
    formData.append('file_type', fileType);

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await axios.post(`${apiUrl}/api/documents/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 10 * 60 * 1000, // 10 minutes for large files
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setUploadProgress(pct);
          }
        },
      });
      onUploadSuccess(response.data);
      setFile(null);
      setUploadProgress(0);
      fetchRecentFiles();
    } catch (error) {
      console.error('Upload failed', error);
      alert('Upload failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <div className="upload-container">
      <h2>Upload Document or Media</h2>
      <div 
        className="upload-box" 
        onClick={() => !uploading && fileInputRef.current.click()} 
        style={{ cursor: uploading ? 'not-allowed' : 'pointer' }}
      >
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={(e) => setFile(e.target.files[0])}
          accept=".pdf,audio/*,video/*"
        />
        {!file ? (
          <>
            <FolderOpen size={48} color="var(--primary-accent)" />
            <p>Click here to select a file</p>
          </>
        ) : (
          <p><FileIcon size={24} color="var(--primary-accent)" /> {file.name}</p>
        )}
      </div>
      {file && (
        <div style={{ marginTop: '16px' }}>
          {file.size > LARGE_FILE_THRESHOLD && (
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', marginBottom: '8px' }}>
              ⚠️ Large file ({(file.size / 1024 / 1024).toFixed(1)} MB) — will be split into chunks for transcription.
            </p>
          )}
          {uploading && uploadProgress > 0 && (
            <div style={{ marginBottom: '10px' }}>
              <div style={{ background: 'var(--bg-secondary, #2a2a3e)', borderRadius: '8px', overflow: 'hidden', height: '8px' }}>
                <div style={{ width: `${uploadProgress}%`, background: 'var(--primary-accent)', height: '100%', transition: 'width 0.3s ease' }} />
              </div>
              <p style={{ fontSize: '0.75rem', textAlign: 'center', marginTop: '4px', color: 'var(--text-muted)' }}>
                Uploading… {uploadProgress}%
              </p>
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <button onClick={handleUpload} disabled={uploading}>
              {uploading ? <Loader className="spin" /> : <Upload />} {uploading ? 'Uploading…' : 'Upload File'}
            </button>
          </div>
        </div>
      )}

      {recentFiles.length > 0 && (
        <div className="recent-files">
          <h3><Clock size={16} /> Recent Files</h3>
          <div className="recent-files-list">
            {recentFiles.map((doc) => (
              <div 
                key={doc.id} 
                className={`recent-file-item ${activeMedia?.id === doc.id ? 'active' : ''}`} 
                onClick={() => onUploadSuccess(doc)}
              >
                <input 
                  type="radio" 
                  checked={activeMedia?.id === doc.id} 
                  readOnly 
                  className="selection-radio"
                />
                <FileIcon size={16} color="var(--primary-accent)" />
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>{doc.title}</span>
                <Trash2 
                  size={16} 
                  className="delete-icon" 
                  onClick={(e) => handleDelete(e, doc.id)} 
                  color="var(--text-muted)"
                />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
