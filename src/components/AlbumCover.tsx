import { useState } from 'react';

interface AlbumCoverProps {
  coverUrl?: string;
  title: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  eraColor?: string;
}

const sizeClasses = {
  sm: 'w-full aspect-square',
  md: 'w-full aspect-square',
  lg: 'w-64 h-64',
};

const iconSizes = {
  sm: 'text-3xl',
  md: 'text-5xl',
  lg: 'text-7xl',
};

// Get initials from album title
function getInitials(title: string): string {
  return title
    .split(' ')
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase();
}

// Generate a consistent color based on title
function getTitleColor(title: string): string {
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
  for (let i = 0; i < title.length; i++) {
    hash = title.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

// Handle image URLs - archive.org and commons work directly, others may need proxy
function getProxiedUrl(url: string): string {
  // Archive.org URLs work directly with CORS
  if (url.includes('archive.org')) {
    return url;
  }
  // Wikipedia Commons images work directly
  if (url.includes('/wikipedia/commons/')) {
    return url;
  }
  // For Wikipedia/en fair use images, use wsrv.nl proxy
  if (url.includes('upload.wikimedia.org')) {
    return `https://wsrv.nl/?url=${encodeURIComponent(url)}&w=400&output=jpg`;
  }
  return url;
}

export function AlbumCover({ coverUrl, title, size = 'md', className = '', eraColor }: AlbumCoverProps) {
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);

  // Only try to load if we have a URL that looks valid
  // Reject fake coverartarchive URLs (text IDs like "zodiac-suite" instead of UUIDs)
  const hasValidUrl = coverUrl &&
    coverUrl.startsWith('http') &&
    !coverUrl.match(/coverartarchive\.org\/release\/[a-z][a-z-]+\/front$/);
  const showFallback = !hasValidUrl || imageError;

  const color = eraColor || getTitleColor(title);
  const initials = getInitials(title);

  return (
    <div
      className={`rounded-lg flex items-center justify-center overflow-hidden relative ${sizeClasses[size]} ${className}`}
      style={{
        backgroundColor: showFallback ? `${color}15` : '#27272a',
        borderColor: showFallback ? `${color}40` : 'transparent',
        borderWidth: showFallback ? '1px' : '0'
      }}
    >
      {!showFallback && coverUrl && (
        <img
          src={getProxiedUrl(coverUrl)}
          alt={`${title} album cover`}
          crossOrigin="anonymous"
          referrerPolicy="no-referrer"
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
            className={`font-bold ${iconSizes[size]}`}
            style={{ color: color }}
          >
            {initials}
          </div>
          <div className={`${size === 'lg' ? 'text-sm' : 'text-xs'} text-zinc-500 mt-1`}>
            {size === 'lg' && 'Album'}
          </div>
        </div>
      )}
      {!showFallback && imageLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-zinc-800">
          <div className={`animate-pulse ${iconSizes[size]}`} style={{ color }}>
            {initials}
          </div>
        </div>
      )}
    </div>
  );
}
