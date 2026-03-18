import type { Album } from '../types';
import { getRecentlyShown } from './localStorage';
import { seededShuffle } from './random';

// ── Types ──

export interface WeatherData {
  temperature: number;
  weatherCode: number;
  isDay: boolean;
}

export interface MoodProfile {
  energy: number;
  warmth: number;
  introspection: number;
  darkness: number;
  groove: number;
}

type MoodKey = keyof MoodProfile;

// ── Weather-to-Mood Mapping ──

const WEATHER_MOOD: Record<string, MoodProfile> = {
  clear:   { energy: 0.7, warmth: 0.7, introspection: 0.2, darkness: 0.1, groove: 0.7 },
  cloudy:  { energy: 0.5, warmth: 0.5, introspection: 0.4, darkness: 0.3, groove: 0.5 },
  fog:     { energy: 0.2, warmth: 0.3, introspection: 0.8, darkness: 0.6, groove: 0.2 },
  drizzle: { energy: 0.3, warmth: 0.4, introspection: 0.7, darkness: 0.5, groove: 0.3 },
  rain:    { energy: 0.3, warmth: 0.3, introspection: 0.8, darkness: 0.6, groove: 0.3 },
  ice:     { energy: 0.2, warmth: 0.1, introspection: 0.7, darkness: 0.7, groove: 0.2 },
  snow:    { energy: 0.2, warmth: 0.2, introspection: 0.9, darkness: 0.4, groove: 0.1 },
  showers: { energy: 0.5, warmth: 0.4, introspection: 0.5, darkness: 0.4, groove: 0.4 },
  storm:   { energy: 0.8, warmth: 0.2, introspection: 0.4, darkness: 0.8, groove: 0.6 },
};

function getWeatherCategory(code: number): string {
  if (code === 0) return 'clear';
  if (code <= 3) return 'cloudy';
  if (code <= 48) return 'fog';
  if (code <= 55) return 'drizzle';
  if (code <= 65) return 'rain';
  if (code <= 67) return 'ice';
  if (code <= 77) return 'snow';
  if (code <= 86) return 'showers';
  return 'storm';
}

// ── Genre-to-Mood Scoring ──

const GENRE_MOOD: Record<string, MoodProfile> = {
  'bebop':               { energy: 0.8, warmth: 0.4, introspection: 0.3, darkness: 0.3, groove: 0.7 },
  'hard bop':            { energy: 0.7, warmth: 0.8, introspection: 0.3, darkness: 0.3, groove: 0.8 },
  'cool jazz':           { energy: 0.3, warmth: 0.5, introspection: 0.7, darkness: 0.3, groove: 0.4 },
  'free jazz':           { energy: 0.8, warmth: 0.2, introspection: 0.6, darkness: 0.8, groove: 0.3 },
  'avant-garde jazz':    { energy: 0.7, warmth: 0.1, introspection: 0.7, darkness: 0.8, groove: 0.2 },
  'soul jazz':           { energy: 0.6, warmth: 0.9, introspection: 0.2, darkness: 0.2, groove: 0.9 },
  'swing':               { energy: 0.7, warmth: 0.7, introspection: 0.1, darkness: 0.1, groove: 0.8 },
  'big band':            { energy: 0.8, warmth: 0.6, introspection: 0.1, darkness: 0.1, groove: 0.8 },
  'jazz fusion':         { energy: 0.8, warmth: 0.5, introspection: 0.3, darkness: 0.3, groove: 0.9 },
  'jazz-funk':           { energy: 0.7, warmth: 0.7, introspection: 0.1, darkness: 0.1, groove: 1.0 },
  'blues':               { energy: 0.4, warmth: 0.8, introspection: 0.5, darkness: 0.5, groove: 0.6 },
  'vocal jazz':          { energy: 0.4, warmth: 0.8, introspection: 0.5, darkness: 0.4, groove: 0.4 },
  'contemporary jazz':   { energy: 0.5, warmth: 0.5, introspection: 0.5, darkness: 0.4, groove: 0.5 },
  'post-bop':            { energy: 0.6, warmth: 0.4, introspection: 0.5, darkness: 0.5, groove: 0.5 },
  'modal jazz':          { energy: 0.4, warmth: 0.5, introspection: 0.8, darkness: 0.4, groove: 0.4 },
  'spiritual jazz':      { energy: 0.5, warmth: 0.6, introspection: 0.9, darkness: 0.4, groove: 0.4 },
  'bossa nova':          { energy: 0.3, warmth: 0.8, introspection: 0.6, darkness: 0.2, groove: 0.6 },
  'latin jazz':          { energy: 0.7, warmth: 0.8, introspection: 0.2, darkness: 0.1, groove: 0.9 },
  'afro-cuban jazz':     { energy: 0.7, warmth: 0.8, introspection: 0.2, darkness: 0.1, groove: 0.9 },
  'early jazz':          { energy: 0.6, warmth: 0.7, introspection: 0.1, darkness: 0.1, groove: 0.7 },
  'dixieland':           { energy: 0.8, warmth: 0.7, introspection: 0.1, darkness: 0.0, groove: 0.8 },
  'smooth jazz':         { energy: 0.3, warmth: 0.8, introspection: 0.4, darkness: 0.1, groove: 0.5 },
  'chamber jazz':        { energy: 0.2, warmth: 0.4, introspection: 0.8, darkness: 0.4, groove: 0.2 },
  'free improvisation':  { energy: 0.7, warmth: 0.1, introspection: 0.8, darkness: 0.7, groove: 0.1 },
  'experimental':        { energy: 0.6, warmth: 0.1, introspection: 0.7, darkness: 0.7, groove: 0.2 },
  'loft jazz':           { energy: 0.5, warmth: 0.3, introspection: 0.7, darkness: 0.6, groove: 0.3 },
  'African jazz':        { energy: 0.7, warmth: 0.7, introspection: 0.3, darkness: 0.2, groove: 0.8 },
  'world fusion':        { energy: 0.5, warmth: 0.6, introspection: 0.4, darkness: 0.3, groove: 0.6 },
  'Brazilian jazz':      { energy: 0.5, warmth: 0.8, introspection: 0.4, darkness: 0.1, groove: 0.7 },
  'piano trio':          { energy: 0.3, warmth: 0.5, introspection: 0.7, darkness: 0.3, groove: 0.4 },
  'acid jazz':           { energy: 0.7, warmth: 0.5, introspection: 0.2, darkness: 0.3, groove: 0.9 },
  'orchestral jazz':     { energy: 0.5, warmth: 0.5, introspection: 0.5, darkness: 0.4, groove: 0.3 },
  'ballad':              { energy: 0.2, warmth: 0.8, introspection: 0.7, darkness: 0.4, groove: 0.2 },
  'third stream':        { energy: 0.4, warmth: 0.3, introspection: 0.7, darkness: 0.5, groove: 0.2 },
};

// Default mood for genres not in the table
const DEFAULT_GENRE_MOOD: MoodProfile = { energy: 0.5, warmth: 0.5, introspection: 0.5, darkness: 0.3, groove: 0.5 };

// ── Build Mood Profile ──

function getTimeOfDay(): 'morning' | 'afternoon' | 'evening' | 'night' {
  const hour = new Date().getHours();
  if (hour >= 6 && hour < 12) return 'morning';
  if (hour >= 12 && hour < 18) return 'afternoon';
  if (hour >= 18 && hour < 23) return 'evening';
  return 'night';
}

function getSeason(): 'spring' | 'summer' | 'autumn' | 'winter' {
  const month = new Date().getMonth();
  if (month >= 2 && month <= 4) return 'spring';
  if (month >= 5 && month <= 7) return 'summer';
  if (month >= 8 && month <= 10) return 'autumn';
  return 'winter';
}

function clamp(v: number): number {
  return Math.max(0, Math.min(1, v));
}

export function buildMoodProfile(weather: WeatherData | null): MoodProfile {
  // Start with a neutral base if no weather
  let mood: MoodProfile = weather
    ? { ...WEATHER_MOOD[getWeatherCategory(weather.weatherCode)] ?? WEATHER_MOOD.cloudy }
    : { energy: 0.5, warmth: 0.5, introspection: 0.4, darkness: 0.3, groove: 0.5 };

  // Temperature modifier
  if (weather) {
    const t = weather.temperature;
    if (t > 30) { mood.energy += 0.1; mood.warmth += 0.1; mood.groove += 0.1; }
    else if (t >= 20) { mood.warmth += 0.05; }
    else if (t >= 10) { mood.introspection += 0.05; }
    else if (t >= 0) { mood.introspection += 0.1; mood.darkness += 0.05; }
    else { mood.darkness += 0.1; mood.introspection += 0.15; }
  }

  // Time-of-day modifier (always applied)
  const time = getTimeOfDay();
  switch (time) {
    case 'morning':
      mood.energy += 0.1; mood.warmth += 0.1; mood.darkness -= 0.1;
      break;
    case 'afternoon':
      mood.groove += 0.1; mood.energy += 0.05;
      break;
    case 'evening':
      mood.warmth += 0.1; mood.introspection += 0.05; mood.darkness += 0.05;
      break;
    case 'night':
      mood.darkness += 0.2; mood.introspection += 0.2; mood.energy -= 0.1;
      break;
  }

  // Season modifier (subtle)
  const season = getSeason();
  switch (season) {
    case 'summer': mood.energy += 0.05; mood.groove += 0.05; break;
    case 'winter': mood.introspection += 0.05; mood.darkness += 0.05; break;
    case 'autumn': mood.warmth += 0.05; mood.introspection += 0.05; break;
    case 'spring': mood.energy += 0.05; mood.warmth += 0.05; break;
  }

  // Clamp all values
  return {
    energy: clamp(mood.energy),
    warmth: clamp(mood.warmth),
    introspection: clamp(mood.introspection),
    darkness: clamp(mood.darkness),
    groove: clamp(mood.groove),
  };
}

// ── Score Albums ──

function scoreAlbum(album: Album, mood: MoodProfile): number {
  const dimensions: MoodKey[] = ['energy', 'warmth', 'introspection', 'darkness', 'groove'];

  if (album.genres.length === 0) return 0;

  let total = 0;
  for (const genre of album.genres) {
    const genreMood = GENRE_MOOD[genre.toLowerCase()] ?? DEFAULT_GENRE_MOOD;
    let dot = 0;
    for (const dim of dimensions) {
      dot += genreMood[dim] * mood[dim];
    }
    total += dot;
  }
  return total / album.genres.length;
}

// ── Get Today's Picks ──

// Pure function: no side effects. Caller is responsible for marking picks as shown.
export function getTodaysPicks(albums: Album[], weather: WeatherData | null): Album[] {
  const mood = buildMoodProfile(weather);
  const recentlyShown = getRecentlyShown();

  // Score all albums with covers
  const withCovers = albums.filter((a) => a.coverUrl);
  const scored = withCovers.map((album) => ({
    album,
    score: scoreAlbum(album, mood),
  }));

  // Sort by score descending
  scored.sort((a, b) => b.score - a.score);

  // Take top pool, excluding recently shown
  const pool: Album[] = [];
  for (const { album } of scored) {
    if (pool.length >= 40) break;
    if (!recentlyShown.has(album.id)) {
      pool.push(album);
    }
  }

  // If pool is too small (edge case), allow recently shown
  if (pool.length < 8) {
    for (const { album } of scored) {
      if (pool.length >= 40) break;
      if (!pool.includes(album)) {
        pool.push(album);
      }
    }
  }

  // Seeded shuffle for deterministic daily picks
  const daySeed = Math.floor(Date.now() / 86400000);
  const shuffled = seededShuffle(pool, daySeed);
  return shuffled.slice(0, 8);
}

// ── Mood Description ──

const WEATHER_LABELS: Record<string, string> = {
  clear: 'Clear skies',
  cloudy: 'Overcast',
  fog: 'Misty',
  drizzle: 'Light rain',
  rain: 'Rainy',
  ice: 'Icy',
  snow: 'Snowy',
  showers: 'Scattered showers',
  storm: 'Stormy',
};

const TIME_LABELS: Record<string, string> = {
  morning: 'morning',
  afternoon: 'afternoon',
  evening: 'evening',
  night: 'late night',
};

export function getMoodDescription(weather: WeatherData | null): string {
  const time = getTimeOfDay();
  const timeLabel = TIME_LABELS[time];

  if (!weather) {
    const descriptions: Record<string, string> = {
      morning: 'Start your morning with something that moves',
      afternoon: 'Afternoon listening -- jazz for the moment',
      evening: 'Evening jazz for winding down',
      night: 'Late night -- time for quiet contemplation',
    };
    return descriptions[time];
  }

  const category = getWeatherCategory(weather.weatherCode);
  const weatherLabel = WEATHER_LABELS[category];
  const temp = Math.round(weather.temperature);

  // Build a descriptive phrase based on dominant mood
  const mood = buildMoodProfile(weather);
  const maxDim = (Object.entries(mood) as [MoodKey, number][])
    .sort((a, b) => b[1] - a[1])[0][0];

  const moodPhrases: Record<MoodKey, string> = {
    energy: 'jazz that hits hard',
    warmth: 'warm, soulful sounds',
    introspection: 'introspective, searching jazz',
    darkness: 'moody, intense listening',
    groove: 'deep grooves and rhythm',
  };

  return `${weatherLabel} ${temp}\u00B0C ${timeLabel} -- ${moodPhrases[maxDim]}`;
}

// ── Weather Emoji ──

export function getWeatherEmoji(weatherCode: number): string {
  const category = getWeatherCategory(weatherCode);
  const emojis: Record<string, string> = {
    clear: '\u2600\uFE0F',
    cloudy: '\u2601\uFE0F',
    fog: '\uD83C\uDF2B\uFE0F',
    drizzle: '\uD83C\uDF26\uFE0F',
    rain: '\uD83C\uDF27\uFE0F',
    ice: '\uD83E\uDDCA',
    snow: '\u2744\uFE0F',
    showers: '\uD83C\uDF26\uFE0F',
    storm: '\u26C8\uFE0F',
  };
  return emojis[category] ?? '\u2601\uFE0F';
}

// ── Fetch Weather ──

export async function fetchWeather(lat: number, lng: number): Promise<WeatherData | null> {
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=temperature_2m,weather_code,is_day`;
    const res = await fetch(url);
    if (!res.ok) return null;
    const data = await res.json();
    return {
      temperature: data.current.temperature_2m,
      weatherCode: data.current.weather_code,
      isDay: data.current.is_day === 1,
    };
  } catch {
    return null;
  }
}
