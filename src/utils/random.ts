// Seeded PRNG for consistent daily content (Linear Congruential Generator)
export function seededShuffle<T>(arr: T[], seed: number): T[] {
  const shuffled = [...arr];
  let s = seed;
  for (let i = shuffled.length - 1; i > 0; i--) {
    s = (s * 16807 + 0) % 2147483647;
    const j = s % (i + 1);
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

export function seededPick<T>(arr: T[], seed: number): T | undefined {
  if (arr.length === 0) return undefined;
  let s = seed;
  s = (s * 16807 + 0) % 2147483647;
  return arr[s % arr.length];
}
