import { siteConfig } from '@site/config';

// Shared fallback color palette for album covers and artist photos
export const FALLBACK_COLORS = siteConfig.fallbackColors;

export function hashColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length];
}
