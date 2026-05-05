import React from 'react';

export default function VideoPlayer({ url }) {
  if (!url) return null;

  return (
    <div className="video-player-wrapper">
      <video controls autoPlay muted src={url}>
        Your browser does not support the video tag.
      </video>
    </div>
  );
}
