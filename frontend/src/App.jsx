import React, { useState } from 'react';
import FileUpload from './components/FileUpload';
import Chat from './components/Chat';
import MediaPlayer from './components/MediaPlayer';
import './App.css';

function App() {
  const [activeMedia, setActiveMedia] = useState(null);
  const [jumpTime, setJumpTime] = useState(null);

  const handleUploadSuccess = (data) => {
    console.log("Media data:", data);
    setActiveMedia(data);
  };

  const handleJumpToTime = (time) => {
    setJumpTime(time);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>AI Multimedia Assistant</h1>
        <p>Upload your PDFs, audio, and videos and ask questions.</p>
      </header>

      <div className="main-content">
        <div className="left-panel">
          <FileUpload onUploadSuccess={handleUploadSuccess} activeMedia={activeMedia} />

          <div className="media-section">
            <h3>Media Player</h3>
            <MediaPlayer
              src={activeMedia ? (activeMedia.file.startsWith('http') ? activeMedia.file : `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${activeMedia.file}`) : null}
              type={activeMedia?.file_type}
              jumpTime={jumpTime}
            />
          </div>
        </div>

        <div className="right-panel">
          <Chat onJumpToTime={handleJumpToTime} activeMedia={activeMedia} />
        </div>
      </div>
    </div>
  );
}

export default App;
