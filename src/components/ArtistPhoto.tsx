import { useState } from 'react';
import { getProxiedUrl } from '../utils/imageProxy';

interface ArtistPhotoProps {
  imageUrl?: string;
  name: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  priority?: boolean;
  className?: string;
}

const sizeClasses = {
  sm: 'w-10 h-10',
  md: 'w-16 h-16',
  lg: 'w-24 h-24',
  xl: 'w-32 h-32',
};

const defaultWidths = {
  sm: 80,
  md: 128,
  lg: 192,
  xl: 256,
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
    '#D95B43', // coral
    '#3B8686', // teal
    '#C7B042', // mustard
    '#556B2F', // olive
    '#1A1A2E', // navy
    '#8B6914', // dark gold
    '#7B4B94', // plum
    '#B8383B', // brick red
  ];

  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}


export function ArtistPhoto({
  imageUrl,
  name,
  size = 'md',
  priority,
  className = '',
}: ArtistPhotoProps) {
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);

  const hasValidUrl = imageUrl && imageUrl.startsWith('http');
  const showFallback = !hasValidUrl || imageError;

  const color = getNameColor(name);
  const initials = getInitials(name);
  const width = defaultWidths[size];

  return (
    <div
      className={`rounded-full flex items-center justify-center overflow-hidden relative border-2 border-border ${sizeClasses[size]} ${className}`}
      style={{
        backgroundColor: showFallback ? `${color}20` : undefined,
      }}
    >
      {!showFallback && (
        <img
          loading={priority ? 'eager' : 'lazy'}
          fetchPriority={priority ? 'high' : 'auto'}
          decoding="async"
          src={getProxiedUrl(imageUrl ?? '', width)}
          alt={`${name} photo`}
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
            className={`font-bold text-warm-gray ${textSizes[size]}`}
            style={{ color }}
          >
            {initials}
          </div>
        </div>
      )}
      {!showFallback && imageLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-border-light">
          <div className={`animate-pulse ${textSizes[size]}`} style={{ color }}>
            {initials}
          </div>
        </div>
      )}
    </div>
  );
}
