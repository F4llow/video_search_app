import React from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import AnalyzePage from './pages/AnalyzePage';
import SearchPage from './pages/SearchPage';
import { Video, Search } from 'lucide-react';

function App() {
  const location = useLocation();

  return (
    <div>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem 2rem', background: 'rgba(255, 255, 255, 0.05)', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '1.5rem' }}>VideoSense AI</h1>
          <p className="subtitle" style={{ margin: 0, fontSize: '0.85rem' }}>Multimodal Search & Analysis</p>
        </div>
        <nav style={{ display: 'flex', gap: '1rem' }}>
          <Link to="/analyze" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', borderRadius: '8px', background: location.pathname === '/analyze' || location.pathname === '/' ? 'var(--primary)' : 'rgba(255, 255, 255, 0.1)', color: 'white', textDecoration: 'none', fontWeight: 500, transition: 'all 0.2s' }}>
            <Video size={18} /> Analyze
          </Link>
          <Link to="/search" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', borderRadius: '8px', background: location.pathname === '/search' ? 'var(--primary)' : 'rgba(255, 255, 255, 0.1)', color: 'white', textDecoration: 'none', fontWeight: 500, transition: 'all 0.2s' }}>
            <Search size={18} /> Search
          </Link>
        </nav>
      </header>

      <main style={{ padding: '2rem' }}>
        <Routes>
          <Route path="/" element={<AnalyzePage />} />
          <Route path="/analyze" element={<AnalyzePage />} />
          <Route path="/search" element={<SearchPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
