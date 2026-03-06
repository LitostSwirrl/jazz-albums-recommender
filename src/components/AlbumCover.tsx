import { useState } from 'react';
import { getProxiedUrl } from '../utils/imageProxy';
import { hashColor } from '../utils/colors';

interface AlbumCoverProps {
  coverUrl?: string;
  title: string;
  size?: 'sm' | 'md' | 'lg';
  pixelWidth?: number;
  priority?: boolean;
  className?: string;
  eraColor?: string;
}

const sizeClasses = {
  sm: 'w-full aspect-square',
  md: 'w-full aspect-square',
  lg: 'w-64 h-64',
};

const defaultWidths = {
  sm: 200,
  md: 500,
  lg: 512,
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
const getTitleColor = hashColor;

// Check if a /front URL has a valid UUID release ID (not a text slug)
const UUID_FRONT_PATTERN = /coverartarchive\.org\/release\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/front$/;
const ANY_FRONT_PATTERN = /coverartarchive\.org\/release\/[^/]+\/front$/;

export function AlbumCover({ coverUrl, title, size = 'md', pixelWidth, priority, className = '', eraColor }: AlbumCoverProps) {
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);

  // Only try to load if we have a URL that looks valid
  // Reject fake coverartarchive URLs:
  // 1. Text IDs like "zodiac-suite" instead of UUIDs — but allow valid UUID /front redirects
  // 2. Fake UUIDs with pattern "-39f8-4c5e-9e5c-1f9c2d8b8d8d" (placeholder suffix)
  const isTextSlugFront = coverUrl
    ? ANY_FRONT_PATTERN.test(coverUrl) && !UUID_FRONT_PATTERN.test(coverUrl)
    : false;
  const hasValidUrl = coverUrl &&
    coverUrl.startsWith('http') &&
    !isTextSlugFront &&
    !coverUrl.includes('-39f8-4c5e-9e5c-1f9c2d8b8d8d');
  const showFallback = !hasValidUrl || imageError;

  const color = eraColor || getTitleColor(title);
  const initials = getInitials(title);
  const width = pixelWidth ?? defaultWidths[size];

  return (
    <div
      className={`rounded-sm flex items-center justify-center overflow-hidden relative border border-border/50 ${sizeClasses[size]} ${className}`}
      style={{
        backgroundColor: showFallback ? `${color}15` : undefined,
      }}
    >
      {!showFallback && coverUrl && (
        <img
          loading={priority ? 'eager' : 'lazy'}
          fetchPriority={priority ? 'high' : 'auto'}
          decoding="async"
          src={getProxiedUrl(coverUrl, width)}
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
          <div className={`${size === 'lg' ? 'text-sm' : 'text-xs'} text-warm-gray mt-1`}>
            {size === 'lg' && 'Album'}
          </div>
        </div>
      )}
      {!showFallback && imageLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-border-light">
          <div className={`animate-pulse ${iconSizes[size]}`} style={{ color }}>
            {initials}
          </div>
        </div>
      )}
    </div>
  );
}
