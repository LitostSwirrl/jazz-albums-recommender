import { useState, useEffect, useCallback } from 'react';
import { SpotifyIcon } from '../icons';
import {
  hasSpotifyClientId,
  getSpotifyAuthUrl,
  exchangeCodeForToken,
  createSpotifyPlaylist,
} from '../../utils/spotifyPlaylist';

interface SaveToSpotifyProps {
  playlistName: string;
  playlistDescription: string;
  tracks: { trackName: string; artistName: string }[];
}

type Status = 'idle' | 'auth' | 'saving' | 'done' | 'error';

export function SaveToSpotify({
  playlistName,
  playlistDescription,
  tracks,
}: SaveToSpotifyProps) {
  const [status, setStatus] = useState<Status>('idle');
  const [result, setResult] = useState<{ url: string; found: number; total: number } | null>(null);
  const [error, setError] = useState('');

  const handleCode = useCallback(
    async (code: string) => {
      setStatus('saving');
      try {
        const token = await exchangeCodeForToken(code);
        const res = await createSpotifyPlaylist(
          token,
          playlistName,
          playlistDescription,
          tracks,
        );
        setResult({ url: res.url, found: res.tracksFound, total: res.tracksTotal });
        setStatus('done');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to create playlist');
        setStatus('error');
      }
    },
    [playlistName, playlistDescription, tracks],
  );

  useEffect(() => {
    function onMessage(e: MessageEvent) {
      if (e.origin !== window.location.origin) return;
      if (e.data?.type !== 'spotify-auth') return;
      handleCode(e.data.code);
    }
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [handleCode]);

  if (!hasSpotifyClientId()) return null;

  const handleClick = async () => {
    if (status === 'done' || status === 'saving') return;
    setStatus('auth');
    setError('');
    const authUrl = await getSpotifyAuthUrl();
    window.open(authUrl, 'spotify-auth', 'width=500,height=700,left=200,top=100');
  };

  if (status === 'done' && result) {
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-[#1DB954]/10 border border-[#1DB954]/30">
        <SpotifyIcon className="w-5 h-5 text-[#1DB954] shrink-0" />
        <span className="text-sm text-charcoal">
          Saved {result.found}/{result.total} tracks!
        </span>
        <a
          href={result.url}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto text-sm font-medium text-[#1DB954] hover:underline"
        >
          Open in Spotify &rarr;
        </a>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-red-50 border border-red-200">
        <span className="text-sm text-red-600">{error}</span>
        <button
          onClick={() => setStatus('idle')}
          className="ml-auto text-sm text-red-600 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={handleClick}
      disabled={status === 'saving' || status === 'auth'}
      className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#1DB954] text-white font-medium hover:bg-[#1ed760] disabled:opacity-60 disabled:cursor-wait transition-colors"
    >
      <SpotifyIcon className="w-5 h-5" />
      {status === 'saving'
        ? 'Saving...'
        : status === 'auth'
          ? 'Connecting...'
          : 'Save to Spotify'}
    </button>
  );
}
