const STORAGE_KEY = 'jazz-guide-todays-picks-history';

interface PickHistory {
  [albumId: string]: string; // ISO date string
}

export function getRecentlyShown(): Map<string, string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Map();
    const parsed: PickHistory = JSON.parse(raw);
    return new Map(Object.entries(parsed));
  } catch {
    return new Map();
  }
}

export function markAsShown(albumIds: string[]): void {
  try {
    const history = getRecentlyShown();
    const today = new Date().toISOString().split('T')[0];
    for (const id of albumIds) {
      history.set(id, today);
    }
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(Object.fromEntries(history))
    );
  } catch {
    // localStorage unavailable, silently fail
  }
}

export function clearOldEntries(daysToKeep: number = 7): void {
  try {
    const history = getRecentlyShown();
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - daysToKeep);
    const cutoffStr = cutoff.toISOString().split('T')[0];

    for (const [id, date] of history) {
      if (date < cutoffStr) {
        history.delete(id);
      }
    }
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(Object.fromEntries(history))
    );
  } catch {
    // localStorage unavailable, silently fail
  }
}
