import { useState } from 'react';

interface AlbumCoverProps {
  coverUrl?: string;
  title: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'w-full aspect-square text-4xl',
  md: 'w-full aspect-square text-6xl',
  lg: 'w-64 h-64 text-8xl',
};

export function AlbumCover({ coverUrl, title, size = 'md', className = '' }: AlbumCoverProps) {
  const [imageError, setImageError] = useState(false);
  const [imageLoading, setImageLoading] = useState(true);

  const showFallback = !coverUrl || imageError;

  return (
    <div
      className={`bg-zinc-800 rounded-lg flex items-center justify-center overflow-hidden ${sizeClasses[size]} ${className}`}
    >
      {!showFallback && (
        <img
          src={coverUrl}
          alt={`${title} album cover`}
          className={`w-full h-full object-cover transition-opacity duration-300 ${
            imageLoading ? 'opacity-0' : 'opacity-100'
          }`}
          onError={() => setImageError(true)}
          onLoad={() => setImageLoading(false)}
        />
      )}
      {(showFallback || imageLoading) && (
        <span className={showFallback ? '' : 'absolute'}>💿</span>
      )}
    </div>
  );
}
