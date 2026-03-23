const SPOTIFY_API = 'https://api.spotify.com/v1';
const PKCE_VERIFIER_KEY = 'spotify_pkce_verifier';

interface SpotifyTrackInput {
  trackName: string;
  artistName: string;
}

interface CreatePlaylistResult {
  url: string;
  tracksFound: number;
  tracksTotal: number;
}

// --- PKCE helpers ---

function generateRandomString(length: number): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  const values = crypto.getRandomValues(new Uint8Array(length));
  return Array.from(values, (v) => chars[v % chars.length]).join('');
}

async function sha256(plain: string): Promise<ArrayBuffer> {
  return crypto.subtle.digest('SHA-256', new TextEncoder().encode(plain));
}

function base64urlEncode(buffer: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buffer)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

// --- Auth ---

export function hasSpotifyClientId(): boolean {
  return !!import.meta.env.VITE_SPOTIFY_CLIENT_ID;
}

function getRedirectUri(): string {
  return `${window.location.origin}${import.meta.env.BASE_URL}`;
}

export async function getSpotifyAuthUrl(): Promise<string> {
  const clientId = import.meta.env.VITE_SPOTIFY_CLIENT_ID;
  if (!clientId) throw new Error('VITE_SPOTIFY_CLIENT_ID not configured');

  const codeVerifier = generateRandomString(64);
  sessionStorage.setItem(PKCE_VERIFIER_KEY, codeVerifier);

  const codeChallenge = base64urlEncode(await sha256(codeVerifier));

  const params = new URLSearchParams({
    client_id: clientId,
    response_type: 'code',
    redirect_uri: getRedirectUri(),
    scope: 'playlist-modify-public user-read-private',
    code_challenge_method: 'S256',
    code_challenge: codeChallenge,
    show_dialog: 'false',
  });

  return `https://accounts.spotify.com/authorize?${params}`;
}

export async function exchangeCodeForToken(code: string): Promise<string> {
  const clientId = import.meta.env.VITE_SPOTIFY_CLIENT_ID;
  const codeVerifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  if (!codeVerifier) throw new Error('PKCE verifier not found');

  const res = await fetch('https://accounts.spotify.com/api/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: clientId,
      grant_type: 'authorization_code',
      code,
      redirect_uri: getRedirectUri(),
      code_verifier: codeVerifier,
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Token exchange failed: ${body}`);
  }

  const data = await res.json();
  sessionStorage.removeItem(PKCE_VERIFIER_KEY);
  return data.access_token;
}

// --- API ---

async function spotifyFetch(path: string, token: string, options?: RequestInit) {
  const res = await fetch(`${SPOTIFY_API}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const reason = body?.error?.message ?? body?.error ?? `HTTP ${res.status}`;
    throw new Error(`Spotify ${res.status} on ${path}: ${reason}`);
  }
  return res.json();
}

export async function createSpotifyPlaylist(
  token: string,
  name: string,
  description: string,
  tracks: SpotifyTrackInput[],
): Promise<CreatePlaylistResult> {
  const user = await spotifyFetch('/me', token);

  const trackUris: string[] = [];
  for (const { trackName, artistName } of tracks) {
    const q = encodeURIComponent(`track:${trackName} artist:${artistName}`);
    const result = await spotifyFetch(`/search?q=${q}&type=track&limit=1`, token);
    const item = result.tracks?.items?.[0];
    if (item) {
      trackUris.push(item.uri);
    }
  }

  const playlist = await spotifyFetch(`/users/${user.id}/playlists`, token, {
    method: 'POST',
    body: JSON.stringify({
      name,
      description: `${description} — curated by Jazz Albums Recommender`,
      public: true,
    }),
  });

  if (trackUris.length > 0) {
    await spotifyFetch(`/playlists/${playlist.id}/tracks`, token, {
      method: 'POST',
      body: JSON.stringify({ uris: trackUris }),
    });
  }

  return {
    url: playlist.external_urls.spotify,
    tracksFound: trackUris.length,
    tracksTotal: tracks.length,
  };
}
