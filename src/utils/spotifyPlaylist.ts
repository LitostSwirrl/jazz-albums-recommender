const SPOTIFY_API = 'https://api.spotify.com/v1';

interface SpotifyTrackInput {
  trackName: string;
  artistName: string;
}

interface CreatePlaylistResult {
  url: string;
  tracksFound: number;
  tracksTotal: number;
}

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
    const body = await res.text();
    throw new Error(`Spotify API ${res.status}: ${body}`);
  }
  return res.json();
}

export function getSpotifyAuthUrl(): string {
  const clientId = import.meta.env.VITE_SPOTIFY_CLIENT_ID;
  if (!clientId) throw new Error('VITE_SPOTIFY_CLIENT_ID not configured');

  const redirectUri = `${window.location.origin}${import.meta.env.BASE_URL}`;
  const scope = 'playlist-modify-public';

  const params = new URLSearchParams({
    client_id: clientId,
    response_type: 'token',
    redirect_uri: redirectUri,
    scope,
    show_dialog: 'false',
  });

  return `https://accounts.spotify.com/authorize?${params}`;
}

export function hasSpotifyClientId(): boolean {
  return !!import.meta.env.VITE_SPOTIFY_CLIENT_ID;
}

export async function createSpotifyPlaylist(
  token: string,
  name: string,
  description: string,
  tracks: SpotifyTrackInput[],
): Promise<CreatePlaylistResult> {
  // 1. Get current user
  const user = await spotifyFetch('/me', token);

  // 2. Search for each track
  const trackUris: string[] = [];
  for (const { trackName, artistName } of tracks) {
    const q = encodeURIComponent(`track:${trackName} artist:${artistName}`);
    const result = await spotifyFetch(`/search?q=${q}&type=track&limit=1`, token);
    const item = result.tracks?.items?.[0];
    if (item) {
      trackUris.push(item.uri);
    }
  }

  // 3. Create playlist
  const playlist = await spotifyFetch(`/users/${user.id}/playlists`, token, {
    method: 'POST',
    body: JSON.stringify({
      name,
      description: `${description} — curated by Jazz Albums Recommender`,
      public: true,
    }),
  });

  // 4. Add tracks (Spotify allows max 100 per request)
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
