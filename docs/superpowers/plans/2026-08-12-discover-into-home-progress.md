# Discover into Home — progress

Goal: merge /discover into Home per spec 2026-08-12-discover-into-home-design.md.

## Steps

- [x] Spec written and approved in-session
- [x] DiscoverSection.tsx created (Tonight grid + 9 shelves, sole importer of rec JSON)
- [x] Home.tsx rewired (drop era/genre/spotlight/quicklinks, lazy DiscoverSection)
- [x] Header.tsx: Discover link removed (desktop + mobile lists)
- [x] App.tsx: /discover → Navigate to /
- [x] Deletions: pages/Discover.tsx, GenreRow, ArtistSpotlight, QuickLinksGrid, pages/index.ts export
- [x] Build clean — DiscoverSection is its own 247KB chunk (51KB gzip); main bundle unchanged
- [x] Mobile (390px): Tonight = 2 cols, all 9 shelves render, no page-level horizontal
      overflow, hamburger menu has no Discover, spin produced an album link
- [x] Desktop (1440px): Tonight = 4 cols, nav has no Discover, #/discover → #/
- [x] CLAUDE.md Landing Page Features updated
- [x] Code review pass (code-reviewer agent) — 3 findings fixed:
      ErrorBoundary around the lazy DiscoverSection (a failed chunk load after a
      deploy would otherwise blank all of Home via the root boundary; fallback
      must be truthy, null falls through), RecCard priority prop removed (last
      caller gone), CarouselSection linkTo/linkLabel removed (last callers were
      the dropped era/genre rows)
- [x] Rebuild + browser re-check after fixes: 12 sections, no error state
- [x] Commit

## Notes

- Usage check done up front: AlbumCarousel used by TodaysPick (keep);
  GenreRow/ArtistSpotlight/QuickLinksGrid used only by Home (delete).
  pages/index.ts barrel is imported by nothing, but the stale Discover export
  would still break tsc after the file deletion, so it gets trimmed.
- RecCard keeps analytics source 'discover' / 'discover_spotify' — still names
  the recommendation system, and renaming would fragment existing Umami data.
- LazySection defers mount until ~200px from viewport; React.lazy inside it
  means the chunk (and the 300KB JSON) fetches only then. Suspense fallback
  mirrors LazySection's h-48 placeholder to avoid layout jump.
- Console during verification: only the long-standing cover-preload warnings
  (usePreloadImages links vs late-rendering imgs); zero errors.
- "Evenings at the Village Gate" in Tonight shows the initials fallback — cover
  missing from recCoverManifest, predates this change; candidate for the next
  fetch_covers run.
- Reviewer items left alone deliberately: AlbumCarousel's 'sm' cardSize branch
  is now caller-less but sits next to an 'lg' branch that was already dead
  before this change — flagged for a separate cleanup, not blended in here.
  Pre-existing and untouched: Home SEO says "275 artists" but artists.json has
  315; RecCard analytics still label clicks source='discover' (renaming would
  fragment existing Umami data).
- Home's unused-import sweep after dropping sections: artistsData, seededShuffle,
  CarouselSection, AlbumCarousel, GenreRows, ArtistSpotlight, QuickLinksGrid all
  removed from Home.tsx; eras stays (HeroFeature + RandomAlbumPicker need it).
