# Spotify URL fill report — 2026-04-14

- Missing before session: 54/1000
- Missing after session: 46/1000
- Newly filled: 8
- Current coverage: 95.4%

Two passes:
1. MusicBrainz URL-relations via `scripts/find_missing_spotify.py` — found 3.
2. Spotify Search API via `scripts/fill_spotify_urls.py` — found 5.

Spec required artist similarity ≥ 0.85 before attaching a URL. The 
remaining 46 albums are legitimately hard to resolve: mostly free 
improv / avant-garde / European jazz reissues / posthumous compilations 
that may not be on Spotify or that Spotify catalogs under a different 
primary artist than the dataset.

## Unresolved albums (manual curation)

- `ammmusic` — **AMMMusic** / AMM (1967)
- `legacy` — **Legacy** / Abraham Burton (2014)
- `nine-compositions-hill-2000` — **Nine Compositions (Hill) 2000** / Anthony Braxton (2000)
- `free-for-all-art-blakey` — **Free for All** / Art Blakey (2012)
- `les-stances-a-sophie` — **Les Stances à Sophie** / Art Ensemble of Chicago (1970)
- `mingus-by-five` — **Mingus By Five** / Bobo Stenson (None)
- `unto-i-am` — **Unto I Am** / Charles Gayle (1995)
- `wild-cat-blues-clarence-williams` — **Wild Cat Blues** / Clarence Williams (None)
- `flowers-for-albert` — **Flowers for Albert** / David Murray (1976)
- `solo-guitar-bailey` — **Solo Guitar** / Derek Bailey (1971)
- `standards` — **Standards** / Derek Bailey (2007)
- `in-the-townships` — **In the Townships** / Dudu Pukwana (1973)
- `bix-beiderbecke-and-frankie-trumbauer-volume-one` — **Bix Beiderbecke and Frankie Trumbauer - Volume One** / Eddie Lang (1991)
- `saxophone-solos` — **Saxophone Solos** / Evan Parker (1975)
- `summit-reunin-cumbre` — **Summit (Reunión cumbre)** / Gerry Mulligan (1974)
- `live-under-the-sky-tokyo-84` — **Live Under The Sky Tokyo '84** / Gil Evans (2016)
- `listen-ship` — **Listen Ship** / Henry Threadgill (2025)
- `when-was-that` — **When Was That?** / Henry Threadgill (1982)
- `tetterettet` — **Tetterettet** / ICP Orchestra (1977)
- `jacos-first-band` — **Jaco's First Band** / Jaco Pastorius (2008)
- `live-under-the-sky-tokyo-84-pastorius` — **Live Under The Sky Tokyo '84** / Jaco Pastorius (2016)
- `the-mezzo-sax-encounter` — **The Mezzo Sax Encounter** / Joe Lovano (2016)
- `soul-junction-coltrane` — **Soul Junction** / John Coltrane (1960)
- `school` — **School** / John Zorn (1978)
- `light-of-the-world` — **Light of the World** / Kamasi Washington (2008)
- `one-poem-one-painting` — **One Poem, One Painting** / Lars Jansson (1998)
- `spirits-rejoice-moholo` — **Spirits Rejoice!** / Louis Moholo-Moholo (1978)
- `concert-in-the-garden` — **Concert in the Garden** / Maria Schneider (2004)
- `winter-morning-walks` — **Winter Morning Walks** / Maria Schneider (2013)
- `messidors-finest-volume-1` — **Messidor's Finest Volume 1** / Mario Bauzá (None)
- `on-the-other-hand` — **On the Other Hand** / Michel Camilo (1990)
- `blues-for-new-orleans` — **Blues For New Orleans** / Phil Woods (2006)
- `the-little-big-band-real-life` — **The Little Big Band: Real Life** / Phil Woods (1991)
- `the-peoples-republic` — **The People's Republic** / Revolutionary Ensemble (1976)
- `the-oscar-peterson-trio-at-newport` — **The Oscar Peterson Trio at Newport** / Roy Eldridge (1958)
- `golden-striker-live-at-theaterstbchen-kassel` — **Golden Striker (Live at Theaterstübchen Kassel)** / Russell Malone (2017)
- `natures-revenge` — **Nature’s Revenge** / Ryo Kawasaki (1978)
- `vital-tech-tones` — **Vital Tech Tones** / Scott Henderson (1998)
- `jazz-in-film` — **Jazz in Film** / Terence Blanchard (1999)
- `herbie-hancock-trio-with-ron-carter-tony-williams` — **Herbie Hancock Trio with Ron Carter + Tony Williams** / Tony Williams (1981)
- `tubbys-new-groove` — **Tubby’s New Groove** / Tubby Hayes (2011)
- `alloy` — **Alloy** / Tyshawn Sorey (2014)
- `inner-spectrum-of-variables` — **Inner Spectrum of Variables** / Tyshawn Sorey (2016)
- `jazz-in-paris-music-on-my-mind` — **Jazz in Paris: Music on My Mind** / Willie "the Lion" Smith (2001)
- `a-smooth-one-woody-herman` — **A Smooth One** / Woody Herman (None)
- `in-the-spirit-of-blues` — **In The Spirit of Blues** / Yuki Arimasa (None)