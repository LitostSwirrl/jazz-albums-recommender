/**
 * Normalize a string for search comparison.
 * Converts curly quotes → straight, en/em dashes → hyphen,
 * strips diacritics, lowercases and trims.
 */
export function normalizeSearchStr(text: string): string {
  return text
    .replace(/[\u2018\u2019]/g, "'")   // curly apostrophes → straight
    .replace(/[\u201c\u201d]/g, '"')   // curly double quotes → straight
    .replace(/[\u2013\u2014]/g, '-')   // en/em dash → hyphen
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')   // strip diacritics (é → e, ü → u)
    .toLowerCase()
    .trim();
}
