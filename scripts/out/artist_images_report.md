# Artist image repair — 2026-04-14

- Targets: 14 (missing or explicitly flagged)
- Repaired: 8
- Unresolved: 6

Scope note: bulk HEAD-verification of all 301 populated `imageUrl` 
values was attempted but Wikimedia's CDN rate-limited the burst (429 
on upload.wikimedia.org). Existing URLs have been working in 
production and were not re-sourced. Only missing URLs and the Art 
Tatum case called out by the S3 spec were touched.

## Repaired
- **Various Artists** (`various-artists`)
  - source: MediaWiki images list (800px thumbnail)
  - old: `<missing>`
  - new: `https://upload.wikimedia.org/wikipedia/commons/c/c3/45_record.png`
- **Jimmy Giuffre** (`jimmy-giuffre`)
  - source: MediaWiki images list (800px thumbnail)
  - old: `<missing>`
  - new: `https://upload.wikimedia.org/wikipedia/en/c/c9/Jimmy_Giuffre.jpg`
- **Shorty Rogers** (`shorty-rogers`)
  - source: MediaWiki images list (800px thumbnail)
  - old: `<missing>`
  - new: `https://upload.wikimedia.org/wikipedia/en/4/4d/Shorty_Rogers.jpg`
- **Wardell Gray** (`wardell-gray`)
  - source: MediaWiki images list (800px thumbnail)
  - old: `<missing>`
  - new: `https://upload.wikimedia.org/wikipedia/en/d/d8/Wardell_Gray.jpg`
- **Booker Ervin** (`booker-ervin`)
  - source: MediaWiki images list (800px thumbnail)
  - old: `<missing>`
  - new: `https://upload.wikimedia.org/wikipedia/en/f/f6/Booker_Ervin.jpg`
- **Oliver Nelson** (`oliver-nelson`)
  - source: MediaWiki images list (800px thumbnail)
  - old: `<missing>`
  - new: `https://upload.wikimedia.org/wikipedia/en/7/72/Oliver_Edward_Nelson.jpg`
- **Kenny Drew** (`kenny-drew`)
  - source: MediaWiki images list (800px thumbnail)
  - old: `<missing>`
  - new: `https://upload.wikimedia.org/wikipedia/en/e/e0/Kenny_Drew.jpg`
- **Thad Jones** (`thad-jones`)
  - source: MediaWiki images list (800px thumbnail)
  - old: `<missing>`
  - new: `https://upload.wikimedia.org/wikipedia/en/6/69/Thad_Jones.jpg`

## Unresolved
- **Art Tatum** (`art-tatum`) — API returned the same URL already on file
- **Yuki Arimasa** (`yuki-arimasa`) — no Wikipedia pageimage or Wikidata P18 resolved
- **Johnny Dodds** (`johnny-dodds`) — no Wikipedia pageimage or Wikidata P18 resolved
- **Jazz Composer's Orchestra** (`jazz-composers-orchestra`) — no Wikipedia pageimage or Wikidata P18 resolved
- **Latin Jazz Quintet** (`latin-jazz-quintet`) — no Wikipedia pageimage or Wikidata P18 resolved
- **Clarence Williams** (`clarence-williams`) — no Wikipedia pageimage or Wikidata P18 resolved