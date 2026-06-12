import { useState, useEffect } from 'react';
import { fetchWeather, type WeatherData } from '../utils/weatherMood';

const SESSION_KEY = 'jazz-guide-weather-cache';

interface CachedWeather {
  data: WeatherData;
  timestamp: number;
}

interface UseWeatherResult {
  weather: WeatherData | null;
  loading: boolean;
  locationDenied: boolean;
}

export function useWeather(): UseWeatherResult {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState(true);
  const [locationDenied, setLocationDenied] = useState(false);

  useEffect(() => {
    // Hydrates from sessionStorage on mount, then falls back to geolocation. The
    // synchronous setState on the cache / no-geolocation paths is intentional on mount.
    /* eslint-disable react-hooks/set-state-in-effect */
    let cancelled = false;

    // Check sessionStorage cache first (valid for 30 minutes)
    try {
      const cached = sessionStorage.getItem(SESSION_KEY);
      if (cached) {
        const parsed: CachedWeather = JSON.parse(cached);
        if (Date.now() - parsed.timestamp < 30 * 60 * 1000) {
          setWeather(parsed.data);
          setLoading(false);
          return;
        }
      }
    } catch {
      // ignore cache errors
    }

    if (!navigator.geolocation) {
      setLocationDenied(true);
      setLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        if (cancelled) return;
        const { latitude, longitude } = position.coords;
        // Round to ~1km precision before sharing with the weather API — enough for
        // weather-mood matching, while handing a less precise location to a third party.
        const data = await fetchWeather(
          Math.round(latitude * 100) / 100,
          Math.round(longitude * 100) / 100
        );
        if (cancelled) return;

        if (data) {
          setWeather(data);
          try {
            sessionStorage.setItem(
              SESSION_KEY,
              JSON.stringify({ data, timestamp: Date.now() })
            );
          } catch {
            // sessionStorage unavailable
          }
        }
        setLoading(false);
      },
      () => {
        if (cancelled) return;
        setLocationDenied(true);
        setLoading(false);
      },
      { timeout: 8000, maximumAge: 600000 }
    );

    /* eslint-enable react-hooks/set-state-in-effect */
    return () => { cancelled = true; };
  }, []);

  return { weather, loading, locationDenied };
}
