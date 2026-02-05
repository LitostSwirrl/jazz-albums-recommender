import { useState } from 'react';

interface ArtistPhotoProps {
  imageUrl?: string;
  name: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  showInstrument?: string;
}

const sizeClasses = {
  sm: 'w-10 h-10',
  md: 'w-16 h-16',
  lg: 'w-24 h-24',
  xl: 'w-32 h-32',
};

const textSizes = {
  sm: 'text-sm',
  md: 'text-xl',
  lg: 'text-3xl',
  xl: 'text-4xl',
};

// Get initials from artist name
function getInitials(name: string): string {
  const parts = name.split(' ');
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// Generate a consistent color based on name
function getNameColor(name: string): string {
  const colors = [
    '#f59e0b', // amber
    '#eab308', // yellow
    '#84cc16', // lime
    '#22c55e', // green
    '#14b8a6', // teal
    '#06b6d4', // cyan
    '#3b82f6', // blue
    '#8b5cf6', // violet
    '#a855f7', // purple
    '#ec4899', // pink
    '#f43f5e', // rose
  ];

  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

// Instrument emoji mapping
const instrumentEmoji: Record<string, string> = {
  'trumpet': '',
  'saxophone': '',
  'piano': '',
  'bass': '',
  'drums': '',
  'guitar': '',
  'trombone': '',
  'vocals': '',
  'vibraphone': '',
  'clarinet': '',
  'flute': '',
  'organ': '',
};

export function ArtistPhoto({
  imageUrl,
  name,
  size = 'md',
  className = '',
  showInstrument
}: ArtistPhotoProps) {
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);

  const hasValidUrl = imageUrl && imageUrl.startsWith('http');
  const showFallback = !hasValidUrl || imageError;

  const color = getNameColor(name);
  const initials = getInitials(name);
  const instrumentIcon = showInstrument ? instrumentEmoji[showInstrument.toLowerCase()] : null;

  return (
    <div
      className={`rounded-full flex items-center justify-center overflow-hidden relative ${sizeClasses[size]} ${className}`}
      style={{
        backgroundColor: showFallback ? `${color}20` : '#27272a',
        borderColor: `${color}60`,
        borderWidth: '2px'
      }}
    >
      {!showFallback && (
        <img
          src={imageUrl}
          alt={`${name} photo`}
          className={`w-full h-full object-cover transition-opacity duration-300 ${
            imageLoading ? 'opacity-0' : 'opacity-100'
          }`}
          onError={() => setImageError(true)}
          onLoad={() => setImageLoading(false)}
        />
      )}
      {showFallback && (
        <div className="flex flex-col items-center justify-center">
          <div
            className={`font-bold ${textSizes[size]}`}
            style={{ color }}
          >
            {initials}
          </div>
          {instrumentIcon && size !== 'sm' && (
            <div className="text-xs mt-0.5">{instrumentIcon}</div>
          )}
        </div>
      )}
      {!showFallback && imageLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-zinc-800">
          <div className={`animate-pulse ${textSizes[size]}`} style={{ color }}>
            {initials}
          </div>
        </div>
      )}
    </div>
  );
}
