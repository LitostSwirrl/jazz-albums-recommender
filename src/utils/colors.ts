// Shared fallback color palette for album covers and artist photos
export const FALLBACK_COLORS = [
  '#6b6358', // early jazz
  '#7a7168', // swing
  '#897f75', // bebop
  '#988d83', // cool jazz
  '#a79b90', // hard bop
  '#b6a99d', // free jazz
  '#c5b8ab', // fusion
  '#d4c7b9', // contemporary
];

export function hashColor(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length];
}
