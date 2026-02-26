import { lazy, Suspense } from 'react';
import { HashRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout';
import { LoadingSkeleton } from './components/LoadingSkeleton';
import { ErrorBoundary } from './components/ErrorBoundary';

// Eager load main pages for fast initial navigation
import { Home } from './pages/Home';
import { Albums } from './pages/Albums';
import { Artists } from './pages/Artists';
import { Eras } from './pages/Eras';

// Lazy load detail pages and heavy components
const Era = lazy(() => import('./pages/Era').then(m => ({ default: m.Era })));
const Artist = lazy(() => import('./pages/Artist').then(m => ({ default: m.Artist })));
const Album = lazy(() => import('./pages/Album').then(m => ({ default: m.Album })));
const Timeline = lazy(() => import('./pages/Timeline').then(m => ({ default: m.Timeline })));
const InfluenceGraph = lazy(() => import('./pages/InfluenceGraph').then(m => ({ default: m.InfluenceGraph })));

function App() {
  return (
    <ErrorBoundary>
      <HashRouter>
        <Suspense fallback={<LoadingSkeleton />}>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Home />} />
              <Route path="/eras" element={<Eras />} />
              <Route path="/era/:id" element={<Era />} />
              <Route path="/artists" element={<Artists />} />
              <Route path="/artist/:id" element={<Artist />} />
              <Route path="/albums" element={<Albums />} />
              <Route path="/album/:id" element={<Album />} />
              <Route path="/timeline" element={<Timeline />} />
              <Route path="/influence" element={<InfluenceGraph />} />
            </Route>
          </Routes>
        </Suspense>
      </HashRouter>
    </ErrorBoundary>
  );
}

export default App;
