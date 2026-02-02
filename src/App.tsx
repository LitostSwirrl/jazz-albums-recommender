import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout';
import { Home, Eras, Era, Artists, Artist, Albums, Album, InfluenceGraph, Timeline } from './pages';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/eras" element={<Eras />} />
          <Route path="/era/:id" element={<Era />} />
          <Route path="/artists" element={<Artists />} />
          <Route path="/artist/:id" element={<Artist />} />
          <Route path="/albums" element={<Albums />} />
          <Route path="/album/:id" element={<Album />} />
          <Route path="/influence" element={<InfluenceGraph />} />
          <Route path="/timeline" element={<Timeline />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
