import React, { useRef, useEffect } from 'react';

const MediaPlayer = ({ src, type, jumpTime }) => {
  const mediaRef = useRef(null);

  useEffect(() => {
    if (mediaRef.current) {
      mediaRef.current.load();
    }
  }, [src]);

  useEffect(() => {
    if (mediaRef.current && jumpTime !== null) {
      mediaRef.current.currentTime = jumpTime;
      mediaRef.current.play();
    }
  }, [jumpTime]);

  if (!src) return <div className="media-placeholder">Select a media file to play</div>;

  return (
    <div className="media-player">
      {type === 'video' ? (
        <video ref={mediaRef} controls src={src} width="100%" />
      ) : type === 'audio' ? (
        <audio ref={mediaRef} controls src={src} style={{ width: '100%' }} />
      ) : (
        <div className="media-placeholder">Preview not available for this file type</div>
      )}
    </div>
  );
};

export default MediaPlayer;
