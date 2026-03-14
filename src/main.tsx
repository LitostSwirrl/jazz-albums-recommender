import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HelmetProvider } from 'react-helmet-async'
import './index.css'
import App from './App.tsx'

// Handle Spotify OAuth callback in popup
if (window.opener && window.location.hash.includes('access_token')) {
  const params = new URLSearchParams(window.location.hash.substring(1));
  const accessToken = params.get('access_token');
  if (accessToken) {
    window.opener.postMessage(
      { type: 'spotify-auth', accessToken },
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
