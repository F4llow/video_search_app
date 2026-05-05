import React, { useState } from 'react';
import SearchBar from '../components/SearchBar';
import SearchResults from '../components/SearchResults';
import VideoPlayer from '../components/VideoPlayer';

export default function SearchPage() {
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [currentVideo, setCurrentVideo] = useState(null);

  const handleSearch = async (query, mode) => {
    setIsSearching(true);
    setSearchError("");
    setSearchResults([]);
    setCurrentVideo(null); // reset video
    try {
      const res = await fetch(`http://localhost:8000/search?q=${encodeURIComponent(query)}&mode=${mode}`);
      const data = await res.json();
      if (!res.ok) {
        setSearchError("❌ Search failed. Please try again.");
        return;
      }
      setSearchResults(data.results || []);
    } catch (err) {
      console.error(err);
      setSearchError('Search failed to connect to backend.');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="container-grid">
      <div className="left-pane">
        {currentVideo ? (
          <div className="glass-panel" style={{ position: 'sticky', top: '2rem' }}>
            <VideoPlayer url={currentVideo} />
            <button className="btn" style={{ width: '100%', marginTop: '1rem' }} onClick={() => setCurrentVideo(null)}>
              Close Video
            </button>
          </div>
        ) : (
          <div className="glass-panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px', color: 'var(--text-secondary)' }}>
            Select a video from the search results to play it.
          </div>
        )}
      </div>

      <div className="right-pane glass-panel">
        <SearchBar onSearch={handleSearch} />
        
        <div style={{ marginTop: '2rem' }}>
          {searchError && (
            <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', borderRadius: '8px', color: '#ef4444', marginBottom: '1rem', fontSize: '0.95rem', textAlign: 'center' }}>
              {searchError}
            </div>
          )}
          
          {isSearching ? (
            <div className="spinner"></div>
          ) : (
            <SearchResults results={searchResults} onPlay={async (filename) => {
              try {
                const res = await fetch(`http://localhost:8000/video_url/${filename}`);
                const data = await res.json();
                setCurrentVideo(data.url);
              } catch(e) {
                console.error(e);
              }
            }} />
          )}
        </div>
      </div>
    </div>
  );
}
