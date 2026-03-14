import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HelmetProvider } from 'react-helmet-async'
import './index.css'
import App from './App.tsx'

// Handle Spotify OAuth PKCE callback in popup
if (window.opener) {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  if (code) {
    window.opener.postMessage(
      { type: 'spotify-auth', code },
      window.location.origin,
    );
    window.close();
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HelmetProvider>
      <App />
    </HelmetProvider>
  </StrictMode>,
)
