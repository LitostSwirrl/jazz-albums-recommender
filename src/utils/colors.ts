// Shared fallback color palette for album covers and artist photos
export const FALLBACK_COLORS = [
  '#C2694F', // burnt sienna
  '#4ECDC4', // teal
  '#D4A843', // mustard
  '#7DA87D', // olive
  '#A06BCA', // plum
  '#C9A84C', // gold
  '#84B4B4', // ice
  '#D04E51', // brick red
];

export function hashColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length];
}
