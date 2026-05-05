import React, { useState } from 'react';
import { Search } from 'lucide-react';

export default function SearchBar({ onSearch }) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('elser');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim(), mode);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <form onSubmit={handleSubmit} className="search-input-wrapper" style={{ margin: 0 }}>
        <input 
          type="text" 
          className="search-input" 
          placeholder={mode === 'elser' ? "Semantic search through your videos..." : "Keyword search..."} 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <Search className="search-icon" size={20} />
      </form>
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', paddingRight: '0.5rem' }}>
        <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
          <input 
            type="radio" 
            value="elser" 
            checked={mode === 'elser'} 
            onChange={() => setMode('elser')}
            style={{ marginRight: '6px' }}
          />
          Semantic (ELSER)
        </label>
        <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
          <input 
            type="radio" 
            value="bm25" 
            checked={mode === 'bm25'} 
            onChange={() => setMode('bm25')}
            style={{ marginRight: '6px' }}
          />
          Keyword (BM25)
        </label>
      </div>
    </div>
  );
}
