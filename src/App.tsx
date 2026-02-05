import { HashRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout';
import { Home } from './pages/Home';
import { Eras } from './pages/Eras';
import { Era } from './pages/Era';
import { Artists } from './pages/Artists';
import { Artist } from './pages/Artist';
import { Albums } from './pages/Albums';
import { Album } from './pages/Album';
import { Timeline } from './pages/Timeline';
import { InfluenceGraph } from './pages/InfluenceGraph';

function App() {
  return (
    <HashRouter>
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
    </HashRouter>
  );
}

export default App;
