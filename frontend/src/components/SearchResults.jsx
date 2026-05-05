import React from 'react';
import { Play } from 'lucide-react';

export default function SearchResults({ results, onPlay }) {
  if (!results || results.length === 0) {
    return <div style={{ color: 'var(--text-secondary)', textAlign: 'center', marginTop: '2rem' }}>No results found.</div>;
  }

  return (
    <div>
      {results.map((res, idx) => (
        <div key={idx} className="result-card">
          <h3>
            {res.filename}
            <span className="score-badge">Score: {res.score.toFixed(2)}</span>
          </h3>
          <p>{res.summary}</p>
          <div className="result-actions">
            <button className="btn-secondary" onClick={() => onPlay(res.filename)}>
              <Play size={16} /> Play Video
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
