import { useEffect } from 'react';
import { getProxiedUrl } from '../utils/imageProxy';

// Injects <link rel="preload"> into <head> for above-the-fold images.
// Browser starts fetching these in parallel with React rendering.
export function usePreloadImages(coverUrls: (string | undefined)[], width: number): void {
  useEffect(() => {
    const links: HTMLLinkElement[] = [];

    for (const url of coverUrls) {
      if (!url) continue;
      const src = getProxiedUrl(url, width);
      const link = document.createElement('link');
      link.rel = 'preload';
      link.as = 'image';
      link.href = src;
      link.setAttribute('fetchpriority', 'high');
      document.head.appendChild(link);
      links.push(link);
    }

    return () => {
      for (const link of links) {
        link.remove();
      }
    };
  }, []); // run once on mount
}
