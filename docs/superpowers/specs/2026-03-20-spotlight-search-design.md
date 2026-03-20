# Spotlight Search - Design Spec

## Overview

A Spotlight-style search overlay that lives in the site header. Searches across 1000 albums and 275 artists with autocomplete results in a translucent floating popup.

## Header Integration

- Magnifying glass icon in the header, right side, before the mobile hamburger toggle
- Click expands the icon into a text input with a smooth transition (icon slides left, input grows from right)
- "X" button or Escape closes back to icon-only
- On mobile, expanded input takes full available header width

## Floating Popup

- Appears below the search input, absolutely positioned, anchored to the right side of the header
- Translucent frosted glass: `backdrop-blur-xl` + semi-transparent dark background (~80% opacity)
- Subtle border and shadow for depth
- Rounded corners, ~400px wide on desktop, full-width on mobile
- Max height ~400px with internal scroll

### Result Layout

Grouped by type:

1. **Artists section** (heading + up to 5 results)
   - Each row: name + instruments (e.g. "Miles Davis -- trumpet")
   - "View all N results" link if more than 5 matches

2. **Albums section** (heading + up to 5 results)
   - Each row: title + artist + year (e.g. "Kind of Blue -- Miles Davis (1959)")
   - "View all N results" link if more than 5 matches

- Hover highlights the row
- No results state: "No results for [query]"

### Dismissal

- Clicking outside the popup
- Pressing Escape
- Selecting a result

All close the popup and reset the search input back to icon-only.

## Search Logic

- Debounced input (300ms)
- Minimum 2 characters before results appear
- Popup only appears when there are results to show (nothing shown on empty input)
- Case-insensitive substring matching via `includes()`
- Fields searched: album title, album artist name, artist name, artist instruments
- Scoring: exact prefix match ranks higher than mid-string match
- Results sorted by score within each group
- Selecting a result navigates to `/artist/:id` or `/album/:id` via React Router

## Component Structure

One new file: `src/components/layout/SearchBar.tsx`

### State

- `isOpen`: boolean -- icon vs expanded input
- `query`: string -- debounced search text
- `results`: filtered and scored artists/albums

### Integration

- Imported into `Header.tsx`, placed in the nav bar
- Imports `albums.json` and `artists.json` directly (already statically bundled)
- Click-outside detection via ref + document event listener
- Escape key listener for dismissal

### No Changes To

- Routing (App.tsx)
- Data loading
- Other components
- No new dependencies
- No new utility files (filtering logic lives in the component)

## Keyboard & Accessibility

- Escape closes the popup and input
- Results are navigable (hover highlights)
- Input has appropriate `aria-label` and `role="combobox"` attributes
- Popup has `role="listbox"`, results have `role="option"`

## Mobile Behavior

- Search icon visible in the header alongside the hamburger
- Expanded input takes full width of header
- Popup is full-width below the header
- Touch-friendly result rows with adequate tap targets
