# Data-Integrity Phase 3 -- Gaps & Human-Review Report

Items Phase 3 did NOT auto-fix, with the reason. Nothing here was guessed; every unresolved item is named honestly. Phase 4 should treat the catalog data errors as the highest priority.

## 1. Catalog data errors (deletion / reattribution candidates) -- HIGH PRIORITY

Web research could not resolve these because the catalog entry itself appears wrong (fabricated, mislabeled, or wrong artist). No safe field repair exists:

- **blue-note-4000**: Not a real album title -- it is the Blue Note 4000-series catalog range. The three 'keyTracks' (Open Sesame, Hub-Tones, Ready for Freddie) are three separate Freddie Hubbard albums. DELETION candidate.
- **investigations**: No Brad Mehldau album by this title exists in his discography. Hallucinated catalog entry. DELETION candidate.
- **new-orleans-joys-kid-ory**: No Kid Ory album by this title; 'New Orleans Joys' is a Jelly Roll Morton solo-piano composition (1923). Misattributed/mislabeled. DELETION or relabel candidate.
- **the-art-of-the-trio-vol-4-nat-king-cole**: WRONG ENTITY: 'The Art of the Trio, Vol. 4: Back at the Vanguard' is a 1999 BRAD MEHLDAU album (Warner Bros.), not Nat King Cole. Reattribute or delete.
- **a-smooth-one-woody-herman**: No Woody Herman album by this title; 'A Smooth One' is a Benny Goodman tune Herman's band played on a 1941 broadcast. Mislabeled track-as-album. DELETION candidate.

Plus an artist/album attribution conflict surfaced during rewrite:
- **lullaby-of-birdland**: catalog says artist *Duke Ellington* (label Intermedia) but ALL evidence (MusicBrainz + Wikipedia) says this is a *Lee Konitz / Barry Harris* date on Candid. Prose was reduced to a bare title+tracks stub. Needs a catalog-level artist decision.

## 2. field_artist -- attribution review (13) -- NOT auto-fixed
These album `artist` fields disagree with the MusicBrainz credit (sideman-vs-leader, or a wrong lead). Left for human decision; MB credit shown:

- **holiday-in-piano**: ours=`Lennie Tristano` | MB credit=`['Lennie Tristano', 'Arnold Ross']` (MB title: 'Holiday in Piano') -- https://musicbrainz.org/release/6bc5db10-0482-497b-9340-faca4299b49e
- **sonny-side-up**: ours=`Sonny Rollins` | MB credit=`['Dizzy Gillespie', 'Sonny Stitt', 'Sonny Rollins']` (MB title: 'Sonny Side Up') -- https://musicbrainz.org/release/9d4b4979-9b75-47cd-a40b-ba84b3712a57
- **cannonball-adderley-and-the-poll-winners**: ours=`Wes Montgomery` | MB credit=`['Cannonball Adderley', 'Ray Brown', 'Wes Montgomery']` (MB title: 'Cannonball Adderley and the Poll-Winners') -- https://musicbrainz.org/release/e59ff189-ad0b-4936-be64-a413ef36fe50
- **soul-junction**: ours=`Donald Byrd` | MB credit=`['The Red Garland Quintet', 'John Coltrane', 'Donald Byrd']` (MB title: 'Soul Junction') -- https://musicbrainz.org/release/0f3c8db2-f276-4c8a-ae95-28f9375038f4
- **jazz-pictures-at-an-exibition**: ours=`Kenny Clarke` | MB credit=`['Pim Jacobs', 'Rita Reys', 'Kenny Clarke']` (MB title: 'Jazz Pictures at an Exibition') -- https://musicbrainz.org/release/f36d7674-a2c1-4a6d-ac89-1a4720861040
- **screamin-the-blues**: ours=`Eric Dolphy` | MB credit=`['Oliver Nelson Sextet', 'Eric Dolphy', 'Richard Williams']` (MB title: "Screamin' the Blues") -- https://musicbrainz.org/release/635f03c6-5b34-47e0-9098-f2882bb1ef3e
- **clarinet-concertos-nos-1-and-2**: ours=`Benny Goodman` | MB credit=`['Weber', 'Benny Goodman', 'Chicago Symphony', 'Jean Martinon']` (MB title: 'Clarinet Concertos Nos. 1 And 2') -- https://musicbrainz.org/release/aa920ce1-ebae-4c95-8cf5-50de194ad9fa
- **breakthrough**: ours=`Cedar Walton` | MB credit=`['Cedar Walton', 'Hank Mobley Quintet']` (MB title: 'Breakthrough!') -- https://musicbrainz.org/release/cafd43f6-2fe3-42cb-a9b2-c2ff41b82c4d
- **illuminations**: ours=`Alice Coltrane` | MB credit=`['Devadip Carlos Santana', 'Turiya Alice Coltrane']` (MB title: 'Illuminations') -- https://musicbrainz.org/release/debbb9a3-40ec-4ac8-97f4-c8b969fea56d
- **third-plane**: ours=`Tony Williams` | MB credit=`['Ron Carter']` (MB title: 'Third Plane') -- https://musicbrainz.org/release/114a07f8-bd59-4f84-9020-8127d28b6ca9
- **third-plane-hancock**: ours=`Herbie Hancock` | MB credit=`['Ron Carter']` (MB title: 'Third Plane') -- https://musicbrainz.org/release/114a07f8-bd59-4f84-9020-8127d28b6ca9
- **concept-of-freedom**: ours=`Duke Ellington` | MB credit=`['Anthony Braxton', 'Duke Ellington']` (MB title: 'Concept of Freedom') -- https://musicbrainz.org/release/d3316ce5-4427-4e4e-9a16-64b847bbf209
- **secrets-are-the-best-stories**: ours=`Danilo Pérez` | MB credit=`['Kurt Elling']` (MB title: 'Secrets Are The Best Stories') -- https://musicbrainz.org/release/db6fffd0-4040-465c-8052-4f93503b9acd

Note: **screamin-the-blues** prose was corrected to leader *Oliver Nelson* (Eric Dolphy is a sideman) per entity-matched evidence, but its `artist` field still reads *Eric Dolphy*. Setting the field to Oliver Nelson would make prose and field consistent.

## 3. year disputed (17) -- left as-is
MusicBrainz first-release year conflicts with ours, but Wikipedia/recording-date evidence is split (often a recorded-one-year / released-another case, e.g. the-olatunji-concert recorded 1967 / released 2001). Not auto-flipped:

- let-freedom-ring: ours=1962 MB=1963 wiki_mentions_ours=False (search sim=1.0 title-match)
- a-caddy-for-daddy: ours=1965 MB=1966 wiki_mentions_ours=False (search sim=1.0 title-match)
- inner-urge: ours=1965 MB=1964 wiki_mentions_ours=False (search sim=1.0 title-match)
- globe-unity: ours=1966 MB=1967 wiki_mentions_ours=False (search sim=1.0 title-match)
- happenings: ours=1966 MB=1967 wiki_mentions_ours=False (search sim=1.0 title-match)
- the-olatunji-concert: ours=1967 MB=2001 wiki_mentions_ours=True (search sim=1.0 title-match)
- for-alto: ours=1969 MB=1971 wiki_mentions_ours=False (search sim=1.0 title-match)
- extensions: ours=1970 MB=1972 wiki_mentions_ours=True (search sim=1.0 title-match)
- live-at-the-lighthouse: ours=1970 MB=1971 wiki_mentions_ours=True (search sim=1.0 title-match)
- saxophone-solos: ours=1975 MB=1976 wiki_mentions_ours=False (search sim=1.0 title-match)
- emerald-tears: ours=1977 MB=1978 wiki_mentions_ours=False (search sim=1.0 title-match)
- betty-carter-album: ours=1979 MB=1988 wiki_mentions_ours=True (search sim=1.0 title-match)
- revue-wsq: ours=1980 MB=1982 wiki_mentions_ours=False (search sim=1.0 title-match)
- tribal-tech: ours=1985 MB=1991 wiki_mentions_ours=False (search sim=1.0 title-match)
- capricorn-rising: ours=1993 MB=1976 wiki_mentions_ours=True (search sim=1.0 title-match)
- inside-hi-fi-lee-konitz: ours=1957 MB=1956 wiki_mentions_ours=False (search sim=1.0 title-match)
- full-house-wes-montgomery: ours=2007 MB=1962 wiki_mentions_ours=True (search sim=1.0 title-match)

## 4. label review (16) -- left as-is
ours has a plausible real label that disagrees with the MB release's label (often original-vs-reissue or a parent conglomerate). Auto-fix would risk regressing a correct original; human picks:

- ella-fitzgerald-sings-the-irving-berlin-song-book: ours='His Master’s Voice' MB labels=['Verve'] url=https://musicbrainz.org/release/333eacea-46b7-4204-b85d-193ffa3662dc
- sonny-side-up: ours='Columbia Records' MB labels=['Verve'] url=https://musicbrainz.org/release/9d4b4979-9b75-47cd-a40b-ba84b3712a57
- screamin-the-blues: ours='Prestige' MB labels=['Original Jazz Classics'] url=https://musicbrainz.org/release/635f03c6-5b34-47e0-9098-f2882bb1ef3e
- sadao-watanabe-mbali: ours='Flying Disk' MB labels=['CBS/Sony', 'CBS/Sony'] url=https://musicbrainz.org/release/b7dbeee4-3e81-433f-807b-9591dee96b71
- domino-theory: ours='CBS/Sony' MB labels=['Columbia'] url=https://musicbrainz.org/release/d2d21a05-6a05-4bea-8570-bd9434aa22a7
- tribal-tech: ours='Passport' MB labels=['Relativity Records'] url=https://musicbrainz.org/release/6dffe946-41b4-40a6-805c-41b13e104fa5
- here-today-tomorrow: ours='Verve' MB labels=['PolyGram Records, Inc.'] url=https://musicbrainz.org/release/0e86a678-892a-423c-bd68-5da98b52648a
- the-man-i-love: ours='AVM Music' MB labels=['Dreyfus Jazz'] url=https://musicbrainz.org/release/93e4b4ce-d864-44fd-b140-71308162d45b
- baboon-moon: ours='Columbia' MB labels=['Sula Records'] url=https://musicbrainz.org/release/a2880b75-ecf6-4e48-b761-218a66caf861
- fearless-movement: ours='Shoto Mas Inc.' MB labels=['Young'] url=https://musicbrainz.org/release/3b76a10d-1fd7-4eab-a537-eb04636a703b
- moondial: ours='BMG' MB labels=['Modern Recordings'] url=https://musicbrainz.org/release/c1742941-0a5e-4edd-b8b1-e6fe68f22c67
- remembrance: ours='Thirty Tigers' MB labels=['Béla Fleck Productions Inc.'] url=https://musicbrainz.org/release/9278ad39-5b50-4d77-871e-8d1650c341b0
- smack: ours='De Agostini' MB labels=['Éditions Atlas'] url=https://musicbrainz.org/release/cd0d437c-1f88-47e9-bb67-b675e1825be5
- bumpin-wes-montgomery: ours='Various' MB labels=['PolyGram Records, Inc.'] url=https://musicbrainz.org/release/e349d209-f2f3-4ffb-b8ba-8286da54262f
- tales-of-captain-black: ours='DIW' MB labels=['Artists House'] url=https://musicbrainz.org/release/553b2d9a-2ab0-38cd-a313-da640294b62c
- snowy-morning-blues: ours='GRP' MB labels=['Verve Reissues'] url=https://musicbrainz.org/release/e274efe0-ddbf-4dbb-ba5d-cefd68215170

## 5. weak MusicBrainz match (10) -- not auto-fixed
MB match was a search hit with low artist-similarity or a title mismatch -- not trusted for an auto fix:

- jay-and-kai (label; no MB release)
- black-christ-of-the-andes (label; no MB release)
- breakthrough (label; MB has no named label)
- music-matador (year; no MB release)
- mercy-mercy-mercy (year; search sim=0.93 title='Mercy, Mercy, Mercy! Live at “The Club”' vs 'Mercy, Mercy, Mercy!')
- in-the-townships (year; search sim=0.77 title='In the Townships' vs 'In the Townships')
- pimp-master (year; no MB release)
- afro-dizzy-gillespie (year; search sim=1.0 title='Afro-Paris / I Cover the Waterfront' vs 'Afro')
- night-train-oscar-peterson (year; search sim=0.76 title='Night Train' vs 'Night Train')
- chet-baker-and-crew-chet-baker (year; search sim=0.77 title='Chet Baker & Crew' vs 'Chet Baker and Crew')

## 6. keyTracks not fixed (16)
- No MB tracklist available (9): looking-ahead, live-at-the-five-spot, the-honeydripper, modern-sounds, music-matador, great-american-songbook, witchi-tai-to, scenery-ryo-fukui, saudades
- Uncertain MB release / title mismatch (7): free-form-harriott (search sim=0.75 title='Free Form' vs 'Free Form'), free-at-last-waldron (search sim=0.81 title='Free at Last' vs 'Free at Last'), in-the-townships (search sim=0.77 title='In the Townships' vs 'In the Townships'), the-popular-duke-ellington (search sim=1.0 title='The Eternal Ellington' vs 'Duke Ellington'), concert-in-the-garden (search sim=0.75 title='Concert in the Garden' vs 'Concert in the Garden'), django-and-his-american-friends-django-reinhardt (search sim=1.0 title='Django And His American Friends, Vol. 2' vs 'Django and His American Friends'), chet-baker-and-crew-chet-baker (search sim=0.77 title='Chet Baker & Crew' vs 'Chet Baker and Crew')

## 7. instrument review (5) -- ours kept, lead-derived differs
ours instruments neither empty nor a clean subset of the lead-derived set; left for review:

- james-carter: ours=['bass clarinetsaxophonesflutes'] derived=['saxophone']
- jazz-epistles: ours=['piano', 'trumpet', 'saxophone', 'bass', 'drums'] derived=['alto saxophone', 'trumpet', 'trombone', 'piano', 'drums', 'bass']
- louis-moholo-moholo: ours=['drums', 'percussion'] derived=['drums']
- ryo-kawasaki: ours=['guitar', 'synthesizer'] derived=['guitar']
- world-saxophone-quartet: ours=['alto saxophone', 'tenor saxophone', 'baritone saxophone', 'soprano saxophone'] derived=['tenor saxophone', 'baritone saxophone', 'soprano saxophone', 'clarinet', 'bass', 'flute']

## 8. thin-evidence prose stubs (7)
Confirmed-bad prose was replaced, but entity-matched evidence was too thin for a full DNA, so a minimal factual stub was written (no invention). Could be enriched later with research:

- blue-notes-legacy
- congo-square
- grazin-in-the-grass
- is-that-so
- lullaby-of-birdland
- mannenberg
- oscar-peterson-plays-george-gershwin

## 9. research: unverifiable compilations (defensible as-is)
Real artist, but the bare title maps to many reissue 'Volume 1' products with different year/label/tracklist; no single release could be confirmed, so no field was changed:

- **his-eye-is-on-the-sparrow-ethel-waters**: UNRESOLVED. 'His Eye Is on the Sparrow' under Ethel Waters resolves to multiple posthumous gospel/sacred COMPILATIONS, not a single canonical album: a Jasmine Records CD (recordings from 1959, reissued 2024), a 2014 Photoplay Records compilation, plus other reissues. No single original release year or label can be confidently assigned. The en.wikipedia.org 'His Eye Is on the Sparrow' article is about the 1905 hymn / Waters's autobiography, NOT an album, so it is not a valid album wikipedia link. Note for catalog: the recordings are late-1950s sacred material, so the site's 'Early Jazz' era tag for this title is likely wrong, but I will not fabricate a year/label. Proposing no repairs.
- **johnny-dodds-vol-1-johnny-dodds**: UNRESOLVED: the bare title 'Johnny Dodds Vol. 1' cannot be pinned to one product. Competing reissue series each have their own 'Volume 1' with different labels/years/tracklists: 'The Chronological Classics: Johnny Dodds 1926' and '1927-1928' (Classics, France, 1991), AllMusic 'Johnny Dodds, Pt. 1 (1926-1940)', and Document Records sets. Artist Johnny Dodds (New Orleans clarinetist, Early Jazz era) is confirmed and the era label is not false, but I cannot verify which release the catalog means, so I propose no year/label/tracklist repair. Not rewriting albumDNA for the same reason: generic but no verifiable false fact to correct against without choosing an unconfirmed specific release.
- **ma-rainey-vol-1-ma-rainey**: UNRESOLVED: the bare title 'Ma Rainey Vol. 1' cannot be pinned to one product. At least two distinct 'Volume 1' reissues exist with different labels, years and tracklists: Document Records 'Complete Recorded Works in Chronological Order, Vol. 1 (December 1923 - August 1924)' (DOCD-5581, CD, 1990s) and Riverside 'Mother of the Blues, Volume 1' (RM 8807, LP, 1960s). Artist Ma Rainey (Gertrude 'Ma' Rainey, blues, Early Jazz era) is confirmed and the era label is not false, but I cannot verify which release the catalog means, so I propose no year/label/tracklist repair. Not rewriting albumDNA: it is generic but contains no verifiable false fact to correct against, and any rewrite would require choosing a specific release I cannot confirm.
- **the-empress-of-the-blues-bessie-smith**: PARTIALLY VERIFIED but UNRESOLVED for field repairs. 'Empress of the Blues' is firmly Bessie Smith's epithet (English Wikipedia: Columbia billed her 'Queen of the Blues', the press 'Empress of the Blues'); her original recordings were for Columbia (1923 on) plus four 1933 Okeh sides. There is NO single canonical studio album titled exactly 'The Empress of the Blues' -- the title attaches to many later compilations (e.g. 'The Empress' 1971 Columbia/Legacy; 'The Empress of the Blues (The Ultimate Collection)' 1998; assorted remastered comps 2010-2013). So a compilation slot with year=null and label='Various' is defensible and I will NOT invent a specific year/label/catalogue. The albumDNA is generic-promotional but not factually false. No reliable single Wikipedia article exists for an album of this exact title (the Bessie Smith biography article is artist-level, not album-level). Marked unresolved; no safe field repair.

## 10. Notes / minor
- **clarence-williams** birthYear set to 1898 (first value in the Wikipedia lead; sources give '1898 or 1893').
- **blue-rondo** and **blue-rondo-brubeck** point to the same MusicBrainz MBID (a 1997 Tudor multi-composer clarinet recital). Both rewritten neutrally; they may be duplicate slots.
- 5 factual_error prose repairs exceed the 600-char house style (kind-of-blue, dizzy-gillespie, ornette-coleman, sonny-rollins, terence-blanchard); each was already over 600 before the surgical fix, and the factual_error rule preserves correct sentences, so they were not trimmed.
- 4 wrong-wiki-link artists (andrew-hill, dave-holland, sadao-watanabe, sam-rivers) and 3 disambiguation-page stub artists (tommy-flanagan, james-moody, clarence-williams) were RESOLVED by research (correct disambiguated Wikipedia URLs + dates/instruments).

