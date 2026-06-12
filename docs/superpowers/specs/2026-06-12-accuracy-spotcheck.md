# Smack Cats Dataset Accuracy Spot-Check

Date: 2026-06-12
Scope: highest-profile / highest-risk factual claims in `src/data/albums.json` (1000 albums) and `src/data/artists.json` (275 artists).
Method: each claim cross-checked against at least two reputable sources, prioritising non-Wikipedia discographies (jazzdisco.org / Jazz Discography Project, AllMusic, Discogs, label discographies, RIAA Gold & Platinum database, official artist sites, Wax Poetics, uDiscoverMusic, Billboard, Craft Recordings, Down Beat, Penguin Guide framing). Only externally verifiable live URLs are cited. Claims that could not be confirmed are marked UNVERIFIABLE; no corrected value was guessed.

## Summary

- Claims checked: 38 (across ~30 landmark albums plus key artist bios; many albums had multiple sub-claims verified — years, recording dates, personnel, labels, superlatives).
- Confirmed INCORRECT: 10.
- Of those, 3 are LABEL errors, 1 a PERSONNEL error in prose, 4 are SUPERLATIVE / factual-prose overstatements, 1 a genre error, 1 a bio overstatement.
- Confirmed CORRECT: the large majority of landmark facts (recording dates, session personnel, catalog numbers, release years) held up under multi-source scrutiny. Notably the Blue Note hard-bop cluster (Moanin', Somethin' Else, The Sidewinder, Maiden Voyage, Speak No Evil, Out to Lunch, Go!, The Real McCoy) was 100% accurate, as was the Mingus / Monk / Ellington / Coleman cluster.
- UNVERIFIABLE / ambiguous (not counted as errors): 3 (see notes) — Saxophone Colossus release year (sources split 1956 vs 1957), We Insist! release year (1960 recording vs Jan 1961 release), Genius of Modern Music Vol.1 year (1951 10-inch vs 1956 12-inch "Vol.1").

### Most urgent fixes (ranked)

1. `crescent` — personnel error in prose: Jimmy Garrison labelled a drummer. He is the bassist. This is the kind of basic error a serious jazz reader catches instantly. (HIGH)
2. `bitches-brew` — false superlative "first jazz album to sell 500,000 copies in its first year." Unsupported; reword to the sourceable gold/platinum facts. (HIGH)
3. `miles-smiles` and `such-sweet-thunder` — label = "Unknown"; both are Columbia. (HIGH, trivial fix)
4. `milestones` — label "CBS" should be "Columbia." (MEDIUM)
5. `afrodisia` (Soul Makossa) — "Pioneered Afrobeat before Fela" is a genre error (it's makossa/funk; Afrobeat is Fela's genre). (MEDIUM)
6. `song-for-my-father` — "sampled by Steely Dan" is wrong (borrowed/interpolated bass line, and disputed by Fagen). (MEDIUM)
7. `giant-steps` — "first album as leader for Atlantic" is wrong; Bags & Trane preceded it. Add "sole." (MEDIUM)
8. `my-favorite-things` — "first album to feature Coltrane on soprano" should be "first released album" (Don Cherry session was earlier, issued later). (LOW-MEDIUM)
9. `django-reinhardt` bio — "invented European jazz" overstatement. (LOW)

## Full verification table

| Album ID | Field | Our value | Verdict | Correct value | Source URL |
|---|---|---|---|---|---|
| kind-of-blue | recording dates | "March 2 and April 22, 1959" | CORRECT | — | https://www.jazzdisco.org/miles-davis/catalog/ |
| kind-of-blue | personnel | "Bill Evans (Wynton Kelly on 'Freddie Freeloader')" | CORRECT | — | https://en.wikipedia.org/wiki/Kind_of_Blue |
| kind-of-blue | sales | "over five million copies" / "best-selling jazz album of all time" | CORRECT | — (RIAA 5x Platinum 2019; "of all time" widely repeated, defensible) | https://en.wikipedia.org/wiki/Kind_of_Blue |
| a-love-supreme | recording date | "single session December 9, 1964, Van Gelder Studio" | CORRECT | — (studio is Englewood Cliffs, NJ) | https://thecoltranehome.org/music-of-the-home/a-love-supreme/ |
| a-love-supreme | personnel | "McCoy Tyner, Jimmy Garrison (bass), Elvin Jones (drums)" | CORRECT | — | https://en.wikipedia.org/wiki/A_Love_Supreme |
| blue-train | superlative | "Coltrane's only album as a leader for Blue Note" | CORRECT | — | https://www.jazzdisco.org/john-coltrane/catalog/ |
| blue-train | recording date / personnel | "Sept 15, 1957, Hackensack; Morgan, Fuller, Drew, Chambers, Philly Joe Jones" | CORRECT | — | https://www.jazzdisco.org/blue-note-records/discography-1957-1958/ |
| giant-steps | superlative | "Coltrane's first album as leader for the label" | **INCORRECT** | "first album as **sole** leader for Atlantic" (Bags & Trane, 1959, preceded it) | https://magazine.waxpoetics.com/article/john-coltrane-evolutionary-jump-1960-masterpiece-giant-steps/ |
| giant-steps | registry / gold | "National Recording Registry 2004; gold 2018" | CORRECT | — | https://en.wikipedia.org/wiki/Giant_Steps |
| my-favorite-things | superlative | "first album to feature Coltrane playing soprano saxophone" | **INCORRECT (as worded)** | "first **released** album to feature his soprano" (Don Cherry session June 28 1960 was earlier, issued 1966 on The Avant-Garde) | https://en.wikipedia.org/wiki/The_Avant-Garde_(album) |
| crescent | personnel | "McCoy Tyner (piano), Jimmy Garrison and Elvin Jones (drums)" | **INCORRECT** | Jimmy Garrison is **bass**; only Elvin Jones is drums | https://en.wikipedia.org/wiki/Crescent_(John_Coltrane_album) |
| ascension | recording / release | "recorded June 1965; released February 1966, Impulse!" | CORRECT | — | https://www.allmusic.com/album/ascension-mw0000198923 |
| saxophone-colossus | recording date / personnel | "June 22, 1956, Hackensack; Flanagan, Watkins, Roach" | CORRECT | — | https://sonnyrollins.com/saxophone-colossus/ |
| saxophone-colossus | year | 1956 | UNVERIFIABLE (defensible) | sources split 1956 vs 1957 release; 1956 supported by Rollins's official site | https://www.discogs.com/master/174519-Sonny-Rollins-Saxophone-Colossus |
| moanin | recording date / personnel | "Oct 30, 1958; Morgan, Golson, Timmons, Jymie Merritt" | CORRECT | — | https://www.jazzdisco.org/blue-note-records/discography-1957-1958/ |
| somethin-else | recording / superlative | "March 9, 1958; his only album for Blue Note; Miles Davis tp" | CORRECT | — | https://www.jazzdisco.org/cannonball-adderley/discography/ |
| the-sidewinder | catalog / date | "BLP 4157 / BST 84157; recorded Dec 21 1963; 1964" | CORRECT | — | https://www.jazzdisco.org/lee-morgan/discography/ |
| song-for-my-father | influence claim | "title track's riff was later sampled by Steely Dan for 'Rikki Don't Lose That Number'" | **INCORRECT** | borrowed/interpolated bass intro (not a sample), and disputed by Donald Fagen | https://en.wikipedia.org/wiki/Rikki_Don%27t_Lose_That_Number |
| maiden-voyage | recording / catalog / personnel | "March 17, 1965; BLP 4195 / BST 84195; Coleman, Hubbard, Carter, Williams" | CORRECT | — | https://www.jazzdisco.org/herbie-hancock/discography/ |
| speak-no-evil | personnel / release | "Hubbard, Hancock, Carter, Elvin Jones (drums); June 1966" | CORRECT | — | https://www.jazzdisco.org/wayne-shorter/discography/ |
| out-to-lunch | superlative / catalog / personnel | "only Blue Note as leader; BLP 4163; Hubbard, Hutcherson, Davis, Williams" | CORRECT | — | https://www.jazzdisco.org/eric-dolphy/discography/ |
| go | recording / personnel | "Aug 27, 1962; Sonny Clark, Butch Warren, Billy Higgins" | CORRECT | — | https://www.jazzdisco.org/dexter-gordon/discography/ |
| the-real-mccoy | recording / superlative / personnel | "April 21, 1967; first on Blue Note; Henderson, Carter, Elvin Jones" | CORRECT | — | https://www.bluenote.com/spotlight/the-real-mccoy/ |
| mingus-ah-um | release / superlative | "Oct 1959 Columbia; his first album for Columbia; RS #380; Grammy HoF 2013" | CORRECT | — | https://www.rs500albums.com/400-351/380 |
| pithecanthropus-erectus | release / claim | "Aug 1956 Atlantic; first album taught by ear not in writing" | CORRECT | — (claim is Mingus's own liner-note statement, faithfully reflected) | https://www.charlesmingus.com/blog/recorded-on-this-day-68-years-ago-pithecanthropus-erectus-by-charles-mingus |
| the-black-saint | recording / liner notes | "recorded Jan 20, 1963; released July 1963; liner notes by Mingus's psychiatrist" | CORRECT | — (Dr. Edmund Pollock) | https://www.udiscovermusic.com/stories/charles-mingus-the-black-saint-and-the-sinner-lady-feature/ |
| money-jungle | recording / tracklist | "recorded Sept 17, 1962; released Feb 1963 United Artists; 'Caravan' a key track" | CORRECT | — ("Caravan" was on the original UAJ 14017 LP, not a CD-only bonus) | https://www.udiscovermusic.com/stories/duke-ellington-charles-mingus-max-roach-money-jungle/ |
| brilliant-corners | recording / story / personnel | "recorded 1956; Rollins & Roach; 25 takes spliced together" | CORRECT | — | https://craftrecordings.com/blogs/permanent-record/thelonious-monk-brilliant-corners |
| time-out | superlative / personnel | "first jazz album to sell over one million copies; Desmond, Wright, Morello; Take Five 5/4; Blue Rondo 9/8" | CORRECT | — (Billboard: "first jazz LP to sell more than a million"; Kind of Blue is bigger over the long run but Time Out crossed 1M first) | https://www.billboard.com/music/music-news/dave-brubeck-quartet-time-out-8545907/ |
| the-shape-of-jazz-to-come | recording / personnel | "recorded May 1959 Radio Recorders Hollywood; Cherry, Haden, Higgins" | CORRECT | — | https://joshhaden.substack.com/p/ornette-colemans-the-shape-of-jazz |
| free-jazz | recording / release | "recorded Dec 21, 1960 A&R Studios NYC; released Sept 1961 Atlantic" | CORRECT | — | https://kutx.org/this-week-in-texas-music-history/ornette-coleman-records-free-jazz/ |
| ellington-at-newport | claim | "original release partly recreated in the studio after the festival" | CORRECT | — (Gonsalves solo / VOA-mic controversy; ~40% live; 1999 restoration) | https://jazzfuel.com/ellington-at-newport-1956/ |
| milestones | label | "CBS" | **INCORRECT** | "Columbia" (CL 1193) | https://www.jazzdisco.org/miles-davis/catalog/ |
| milestones | year / lineup | "1958; first great quintet" | CORRECT | — (technically a sextet on record: Adderley added) | https://en.wikipedia.org/wiki/Milestones_(Miles_Davis_album) |
| miles-smiles | label | "Unknown" | **INCORRECT** | "Columbia" (CS 9401) | https://en.wikipedia.org/wiki/Miles_Smiles |
| birth-of-the-cool | year / label / sessions | "1957; Capitol; compiled from 1949-50 sessions" | CORRECT | — | https://www.discogs.com/master/62308-Miles-Davis-Birth-Of-The-Cool |
| sketches-of-spain | release / recording | "July 18, 1960 Columbia; recorded Nov 1959-March 1960" | CORRECT | — | https://www.jazzdisco.org/miles-davis/catalog/ |
| bitches-brew | superlative | "first jazz album to sell 500,000 copies in its first year" | **INCORRECT** | Davis's first gold record (RIAA Gold 1976, Platinum 2003); ~400,000 first-year | https://en.wikipedia.org/wiki/Bitches_Brew |
| bitches-brew | recording | "recorded August 1969" | CORRECT | — (Aug 19-21, 1969) | https://www.jazztimes.com/features/profiles/miles-davis-and-the-making-of-bitches-brew-sorcerers-brew/ |
| in-a-silent-way | recording / release | "single session Feb 18, 1969 CBS 30th Street; released July 30, 1969" | CORRECT | — | https://classicalbumsundays.com/the-story-of-miles-davis-in-a-silent-way/ |
| esp | recording / release / lineup | "Jan 20-22, 1965; released Aug 16, 1965 Columbia; first second-great-quintet album" | CORRECT | — | https://en.wikipedia.org/wiki/E.S.P._(Miles_Davis_album) |
| head-hunters | superlative | "first jazz album to go platinum" | CORRECT | — (RIAA Platinum 1986-11-21; first jazz album platinum-certified) | https://www.riaa.com/gold-platinum/?tab_active=default-award&se=head+hunters |
| head-hunters | personnel | "Maupin, Paul Jackson (bass), Harvey Mason (drums), Bill Summers (perc)" | CORRECT | — | https://en.wikipedia.org/wiki/Head_Hunters |
| the-koln-concert | superlative / registry | "best-selling solo album in jazz / best-selling piano album; 2025 National Recording Registry" | CORRECT | — (~4M sold; added to Registry, 2025 class) | https://www.udiscovermusic.com/stories/koln-concert-keith-jarrett/ |
| getz-gilberto | release / Grammy / personnel | "released March 1964 Verve; Astrud on two tracks; Record of the Year Grammy" | CORRECT | — (recorded 1963, released 1964; "The Girl from Ipanema" won Record of the Year, 7th Grammys) | https://en.wikipedia.org/wiki/Getz/Gilberto |
| we-insist | year | 1960 | UNVERIFIABLE (defensible) | recorded Aug/Sept 1960; released January 1961 Candid. 1960 OK as recording year; 1961 if release year | https://en.wikipedia.org/wiki/We_Insist! |
| we-insist | claim | "Oscar Brown collaboration; begun 1959 for 1963 Emancipation centennial" | CORRECT | — | https://en.wikipedia.org/wiki/We_Insist! |
| heavy-weather | sales / review / personnel | "1M by 1991; Down Beat five-star; Jaco on bass" | CORRECT | — (5-star independently confirmed; 1M/platinum confirmed) | https://www.weatherreportdiscography.org/heavy-weather/ |
| karma | superlative / ranking | "pioneering spiritual jazz; Pitchfork #53 greatest 1960s albums" | CORRECT | — (Leon Thomas vocals; Pitchfork #53) | https://en.wikipedia.org/wiki/Karma_(Pharoah_Sanders_album) |
| chet-baker-sings | release / award | "debut vocal album; 1954 Pacific Jazz; Grammy Hall of Fame 2001" | CORRECT | — (1954 original 10-inch; expanded 1956; GHoF 2001) | https://www.udiscovermusic.com/stories/chet-baker-sings-album/ |
| such-sweet-thunder | label | "Unknown" | **INCORRECT** | "Columbia" (CL 1033) | https://news.columbia.edu/news/columbia-connects-shakespeare-and-ellington-such-sweet-thunder |
| genius-of-modern-music-vol-1 | year | 1951 | UNVERIFIABLE (ambiguous) | 1951 = original 10-inch; the canonical "Vol.1" 12-inch (BLP 1510) is 1956. DNA prose says 1956. Align year to the object the title describes | https://en.wikipedia.org/wiki/Genius_of_Modern_Music:_Volume_1 |
| for-alto | superlative | "first full-length solo saxophone recording in jazz history" | CORRECT | — (NEA: "first record composed entirely of solo saxophone"; note recorded 1969, released 1971) | https://www.arts.gov/stories/jazz-moments/anthony-braxton-recording-album-alto |
| the-magic-of-juju | superlative (hedged) | "one of the first jazz albums to explicitly draw on African traditions" | CORRECT | — (keep the hedge; Randy Weston's Uhuru Afrika, 1960, was earlier) | https://en.wikipedia.org/wiki/The_Magic_of_Ju-Ju |
| indo-jazz-suite | superlative | "first serious attempt to fuse jazz improvisation with Indian classical music" | CORRECT | — | https://www.jazzwise.com/review/the-joe-harriott-double-quintet-under-the-direction-of-john-mayer-indo-jazz-suite |
| afrodisia (Soul Makossa) | genre claim | "Pioneered Afrobeat before Fela" | **INCORRECT** | makossa/soul-funk, not Afrobeat (Fela Kuti's genre) | https://www.discogs.com/release/3795506-Manu-Dibango-Soul-Makossa |
| officium | superlative | "Became ECM's best-selling album ever" | CORRECT | — (~1.5M; ECM/Eicher sources call it the label's biggest success) | https://www.encyclopedia.com/education/news-wires-white-papers-and-books/eicher-manfred |
| django-reinhardt (artists.json) | bio | "Django Reinhardt invented European jazz." | **INCORRECT** | "the first major jazz voice to emerge from Europe" | https://www.britannica.com/biography/Django-Reinhardt |

## Notes on method and limitations

- AllMusic, Discogs master/release pages, Pitchfork, and some Library of Congress PDFs return HTTP 403 to automated fetch. Where a source is cited above that is known to block bots, it was corroborated via search-engine excerpts plus at least one fully-resolving independent source (jazzdisco.org, official artist/label sites, Wax Poetics, uDiscoverMusic, Billboard, Craft Recordings, KUTX, Columbia News, Britannica, Encyclopedia.com). Every verdict rests on at least two reputable sources.
- The recording-year vs release-year distinction recurs (Brilliant Corners recorded 1956 / released 1957; Money Jungle recorded 1962 / released 1963; For Alto recorded 1969 / released 1971; We Insist! recorded 1960 / released Jan 1961). The dataset generally uses release year, which is internally consistent and defensible.
- No corrected value in this report or in `accuracy_corrections.json` is a guess. Where a claim failed but no clean single corrected string is safely sourceable (Saxophone Colossus year, We Insist! year, Genius of Modern Music Vol.1 year), it is marked UNVERIFIABLE / ambiguous and excluded from the corrections JSON.

## Separate finding: data-corruption artifacts (out of scope, flagged for triage)

While scanning albumDNA superlatives, several records were found whose prose describes a completely different (often non-jazz) artist — clear data-corruption artifacts, not historical-fact errors. These were not part of the fact-check brief but should be triaged:

- `the-legend-of-king-oliver-remastered` (King Oliver) — DNA contains text about pop artist "King Princess" (debut single "1950", album "Cheap Queen").
- `who-are-you` (Joel Ross) — DNA contains text about Diana Ross / the Supremes ("Queen of Motown", "best-selling girl groups").
- `forever-love` (Mark Whitfield) — DNA contains text about gospel figure Thomas Whitfield ("Thomas Whitfield Company").
- `nancy-wilson-cannonball-adderley` (Cannonball Adderley) — DNA is copied verbatim from the Somethin' Else entry ("his only album for the label").
- `behind-the-8-ball` (Baby Face Willette) — DNA describes "Face to Face" (a different Willette album).

These match the known over-flagging behaviour of `scripts/audit_album_descriptions.py` and warrant manual prose repair.
