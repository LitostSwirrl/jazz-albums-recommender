export type AnalyticsProps = Record<string, string | number | boolean>;

export type AlbumClickSource =
  | 'home_carousel'
  | 'album_grid'
  | 'related'
  | 'todays_pick'
  | 'search'
  | 'artist_page'
  | 'random';

export function track(event: string, props?: AnalyticsProps): void {
  if (typeof window === 'undefined' || !window.umami) return;
  window.umami.track(event, props);
}
