import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import type { Album, Artist } from '../../types';
import { getRandomAlbum, getRandomArtist } from '../../utils/discovery';

interface SurpriseButtonProps {
  albums: Album[];
  artists: Artist[];
  variant?: 'button' | 'icon' | 'text';
  className?: string;
}

export function SurpriseButton({ albums, artists, variant = 'button', className = '' }: SurpriseButtonProps) {
  const navigate = useNavigate();

  const handleSurprise = useCallback(() => {
    // 60% chance album, 40% chance artist
    const isAlbum = Math.random() < 0.6;

    if (isAlbum) {
      const album = getRandomAlbum(albums);
      if (album) {
        navigate(`/album/${album.id}`);
      }
    } else {
      const artist = getRandomArtist(artists);
      if (artist) {
        navigate(`/artist/${artist.id}`);
      }
    }
  }, [albums, artists, navigate]);

  if (variant === 'icon') {
    return (
      <button
        onClick={handleSurprise}
        className={`p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-amber-400 hover:text-amber-300 transition-colors ${className}`}
        title="Surprise me!"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
          />
        </svg>
      </button>
    );
  }

  if (variant === 'text') {
    return (
      <button
        onClick={handleSurprise}
        className={`text-amber-400 hover:text-amber-300 transition-colors ${className}`}
      >
        Surprise Me
      </button>
    );
  }

  return (
    <button
      onClick={handleSurprise}
      className={`px-4 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-black font-medium transition-colors flex items-center gap-2 ${className}`}
    >
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
        />
      </svg>
      Surprise Me
    </button>
  );
}
