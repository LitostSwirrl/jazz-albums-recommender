// Warm a lazy route's code + data chunk on hover/focus so the click feels instant.
// The dynamic import() resolves to the same chunk the router lazy-loads, so this is a
// no-op once warmed, and the service worker keeps it cached afterward.
const loaders: Record<string, () => Promise<unknown>> = {
  album: () => import('../pages/Album'),
  artist: () => import('../pages/Artist'),
};

const warmed = new Set<string>();

export function prefetchRoute(route: keyof typeof loaders): void {
  if (warmed.has(route)) return;
  warmed.add(route);
  loaders[route]().catch(() => warmed.delete(route));
}
