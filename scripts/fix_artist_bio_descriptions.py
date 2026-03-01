#!/usr/bin/env python3
"""
Fix albums that have artist biography text as their descriptions.
The Wikipedia search phase returned artist pages instead of album pages.

This script:
1. Detects albums with artist-bio descriptions
2. Re-searches Wikipedia with STRICTER validation (album title must appear in extract)
3. Falls back to metadata-based generation for remaining albums
4. Applies fixes directly to albums.json
"""

import json
import os
import sys
import re
import time
import hashlib
import urllib.request
import urllib.parse
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
CACHE_FILE = '/tmp/artist_bio_fix_cache.json'

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/2.1 (educational; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

# Bio patterns that indicate artist biography, not album description
BIO_PATTERNS = [
    r'^[A-Z][\w\s\"\'.]+(?:is|was) an? (?:American|South African|Cuban|Brazilian|Japanese|British|French|German|Italian|Canadian|Australian|Puerto Rican|Norwegian|Polish|Dutch|Indian|Trinidadian|Belgian|Swedish|Israeli|Ethiopian|Panamanian|Armenian|Danish|Scottish|Irish|Swiss|Austrian|Finnish|Mexican|Barbadian|Guyanese|Venezuelan|Korean|Chinese|Thai|Filipino|Indonesian|Nigerian|Ghanaian|Kenyan|Congolese|Cameroonian|Senegalese|Malian|Guinean|Cape Verdean|Mozambican|Zimbabwean|Tanzanian|Ugandan) (?:jazz |latin |Latin |)',
    r'^[A-Z][\w\s\"\'.]+(?:is|was) an? (?:jazz |Latin )?(?:musician|pianist|saxophonist|trumpeter|drummer|bassist|guitarist|vocalist|singer|organist|vibraphonist|trombonist|composer|bandleader|flutist|clarinetist|cornetist|songwriter|arranger|percussionist|multi-instrumentalist|harmonica player|harpist|cellist|violinist|keyboardist)',
    r'^[A-Z][\w\s\"\'.]+(?:is|was) an? (?:musician|pianist|saxophonist|trumpeter|drummer|bassist|guitarist|vocalist|singer|organist|vibraphonist|trombonist|composer|bandleader|flutist|clarinetist|cornetist|songwriter|arranger|percussionist|multi-instrumentalist)',
    r'^[A-Z][\w\s\"\'.,]+\(\w+ \d{1,2}, \d{4}',  # Name (Month DD, YYYY - birth date
    r'^[A-Z][\w\s\"\'.]+\bborn\b',
]

BANNED_DESC_PHRASES = [
    r'balances technical mastery and emotional depth',
    r'stylistic breadth and global awareness',
    r'anchor the program',
    r'improvisational gifts',
    r'essential chapter in .* recorded output',
    r'creative peak, blending',
    r'pulses with the soulful intensity',
    r'ventures into adventurous',
    r'Notable tracks include',
    r'reflects the communal, improvisational spirit',
    r'crafts a .* session',
    r'recorded output, rooted in',
    r'The arrangement carries the rhythmic drive',
    r'The performances bristle with',
    r'features tracks such as',
    r'The album blends elements of',
    r'The album features tracks such as',
]

BANNED_SIG_PHRASES = [
    r'important entry in .* discography',
    r'noteworthy album',
    r'key chapter in .* evolving artistic vision',
    r'command of .* and their place within',
    r'essential document of .* artistry',
    r'leading voice in',
    r'creative work during this period',
    r'showcasing their contribution to',
    r'reputation as a',
    r'broader jazz lineage',
]

BAD_WIKI_INDICATORS = [
    'may refer to', 'disambiguation', 'is a list of', 'discography of',
    'may also refer to', 'is the discography',
]

MUSIC_INDICATORS = [
    'album', 'record', 'recording', 'studio', 'released', 'label',
    'tracks', 'composed', 'quintet', 'quartet', 'trio', 'ensemble',
    'orchestra', 'bebop', 'swing', 'fusion', 'bop', 'improvisation',
]

LABEL_CONTEXT = {
    'Blue Note': 'Blue Note, under Alfred Lion and Francis Wolff, was the definitive hard bop label, with Rudy Van Gelder engineering many of its classic sessions.',
    'Prestige': 'Prestige under Bob Weinstock was known for its prolific output of blowing sessions, often recording a full album in a single day.',
    'Riverside': 'Riverside, led by Orrin Keepnews, helped launch or revive careers for Monk, Bill Evans, and others.',
    'Impulse!': "Impulse! Records, 'the house that Trane built,' championed both the mainstream and the avant-garde.",
    'ECM': "ECM under Manfred Eicher cultivated 'the most beautiful sound next to silence,' favoring spacious, reverberant recordings.",
    'Columbia': 'Columbia Records gave jazz wide exposure, releasing landmark albums by Miles Davis, Thelonious Monk, and Dave Brubeck.',
    'Verve': "Norman Granz's Verve label was home to swing and vocal jazz royalty, from Ella Fitzgerald to Oscar Peterson.",
    'Pacific Jazz': 'Pacific Jazz Records, run by Richard Bock, defined the West Coast cool sound from its Los Angeles base.',
    'Contemporary': 'Contemporary Records in Los Angeles documented the West Coast jazz scene with high-fidelity engineering.',
    'Atlantic': 'Atlantic Records bridged R&B and jazz with groundbreaking recordings by Coltrane, Mingus, and Coleman.',
    'CTI': "Creed Taylor's CTI label presented jazz in polished, crossover-friendly productions.",
    'Strata-East': 'Strata-East was a musician-owned cooperative label, giving artists full creative control.',
    'Fantasy': 'Fantasy Records in Berkeley documented a wide range of jazz from its Bay Area base.',
    'Concord': 'Concord Records specialized in mainstream and traditional jazz.',
    'Savoy': "Savoy Records documented early bebop, including Charlie Parker's landmark sessions.",
    'Dial': "Dial Records captured some of Charlie Parker's most inspired West Coast recordings.",
    'Milestone': 'Milestone Records documented McCoy Tyner and other post-bop musicians.',
    'Enja': 'The German Enja label documented American and European creative jazz.',
    'Nonesuch': 'Nonesuch Records bridged jazz, world music, and classical.',
    'Candid': 'Candid Records, briefly run by Nat Hentoff, captured politically charged jazz in the early 1960s.',
    'Decca Records': 'Decca Records captured swing era big bands and early jazz vocalists.',
    'Muse': 'Muse Records provided a home for mainstream jazz in the 1970s and 80s.',
    'GRP': 'GRP Records was a leading smooth and contemporary jazz label in the 1980s and 90s.',
    'Pi Recordings': 'Pi Recordings documents the contemporary jazz avant-garde.',
    'Clean Feed': 'The Portuguese Clean Feed label is a leading outlet for contemporary creative jazz.',
    'Tzadik': "John Zorn's Tzadik label spans the avant-garde from jazz to experimental music.",
}

ERA_CONTEXT = {
    'early-jazz': 'the formative years when jazz coalesced from ragtime, blues, and marching band traditions',
    'swing': "the big band era when jazz was America's popular music, driven by dancing and radio",
    'bebop': 'the bebop revolution, when small groups pushed jazz toward harmonic complexity and virtuosity',
    'cool-jazz': 'the cool jazz movement, favoring lighter timbres, relaxed tempos, and a chamber sensibility',
    'hard-bop': "the hard bop period, reconnecting jazz with blues and gospel while keeping bebop's sophistication",
    'free-jazz': 'the free jazz era, when musicians abandoned predetermined structures for collective expression',
    'fusion': 'the jazz-rock fusion era, embracing electric instruments and rhythms from rock and funk',
    'contemporary': "the contemporary era's stylistic eclecticism, drawing on the full history of jazz and beyond",
}

INSTRUMENT_ROLE = {
    'piano': 'pianist', 'trumpet': 'trumpeter', 'saxophone': 'saxophonist',
    'tenor saxophone': 'tenor saxophonist', 'alto saxophone': 'alto saxophonist',
    'soprano saxophone': 'soprano saxophonist', 'baritone saxophone': 'baritone saxophonist',
    'trombone': 'trombonist', 'drums': 'drummer', 'bass': 'bassist',
    'double bass': 'bassist', 'guitar': 'guitarist', 'vibraphone': 'vibraphonist',
    'organ': 'organist', 'clarinet': 'clarinetist', 'flute': 'flutist',
    'vocals': 'vocalist', 'cornet': 'cornetist', 'violin': 'violinist',
    'harmonica': 'harmonicist', 'electric guitar': 'guitarist',
    'electric bass': 'bassist', 'keyboards': 'keyboardist',
    'synthesizer': 'keyboardist', 'percussion': 'percussionist',
    'cello': 'cellist', 'banjo': 'banjoist', 'tuba': 'tuba player',
}


def _variant(seed, n):
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return h % n


def _api_get(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 503):
                time.sleep(3 * (attempt + 1))
                continue
            return None
        except Exception:
            if attempt < 2:
                time.sleep(2)
                continue
            return None
    return None


def _trim_to_sentences(text, max_len):
    if len(text) <= max_len:
        return text
    truncated = text[:max_len + 50]
    sentences = re.split(r'(?<=[.!?])\s+', truncated)
    result = ''
    for s in sentences:
        if len(result) + len(s) + 1 > max_len:
            break
        result = (result + ' ' + s).strip()
    return result if len(result) > 100 else text[:max_len].rsplit('.', 1)[0] + '.'


def _format_tracks(tracks):
    quoted = [f'"{t}"' for t in tracks]
    if len(quoted) == 1:
        return quoted[0]
    if len(quoted) == 2:
        return f'{quoted[0]} and {quoted[1]}'
    return ', '.join(quoted[:-1]) + f', and {quoted[-1]}'


def _a_or_an(word):
    if not word:
        return 'a'
    return 'an' if word[0].lower() in 'aeiou' else 'a'


def is_bio_description(desc):
    """Check if description is an artist biography, not album description."""
    if not desc or len(desc) < 50:
        return False
    for pat in BIO_PATTERNS:
        if re.match(pat, desc):
            return True
    return False


def is_formulaic(text, phrases):
    if not text:
        return True
    lower = text.lower()
    for phrase in phrases:
        if re.search(phrase.lower(), lower):
            return True
    return False


def strict_validate_wiki_extract(extract, album):
    """
    STRICT validation: the extract must be about the ALBUM, not just the artist.
    Key difference from original: requires album title to appear in the extract.
    """
    if not extract or len(extract) < 50:
        return False

    lower = extract.lower()

    # Reject disambiguation pages
    for bad in BAD_WIKI_INDICATORS:
        if bad in lower:
            return False

    # Must contain music indicators
    if not any(w in lower for w in MUSIC_INDICATORS):
        return False

    # Must mention the album title (key improvement over original)
    title = album['title']
    clean_title = re.sub(r'\s*\(.*?\)', '', title).strip().lower()
    title_words = [w for w in clean_title.split() if len(w) > 3 and w not in {'the', 'and', 'with', 'from', 'for'}]

    title_found = (
        clean_title in lower
        or all(w in lower for w in title_words if len(title_words) <= 3)
    )

    if not title_found:
        return False

    # Must mention artist
    artist = album['artist']
    artist_lower = artist.lower()
    artist_parts = artist_lower.split()
    artist_last = artist_parts[-1] if artist_parts else ''

    artist_found = (
        artist_lower in lower
        or artist_last in lower
        or (artist_lower.startswith('the ') and artist_lower[4:] in lower)
    )

    if not artist_found:
        common = {'the', 'and', 'with', 'for', 'from', 'his', 'her'}
        significant = [w for w in artist_parts if len(w) > 3 and w not in common]
        artist_found = any(w in lower for w in significant)

    if not artist_found:
        return False

    # Reject if this looks like an artist bio
    if is_bio_description(extract):
        return False

    # Year check
    album_year = album.get('year')
    if album_year:
        years_in_text = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', extract)
        if years_in_text:
            closest = min(abs(int(y) - album_year) for y in years_in_text)
            if closest > 10:
                return False

    return True


def search_wikipedia_strict(album):
    """Search Wikipedia with strict album-title validation."""
    title = album['title']
    artist = album['artist']
    clean_title = re.sub(r'\s*\(.*?\)', '', title).strip()

    # More targeted queries
    queries = [
        f'{clean_title} ({artist} album)',
        f'{clean_title} (album)',
        f'{clean_title} {artist} album',
    ]

    for query in queries:
        # Try direct page access first
        encoded = urllib.parse.quote(query.replace(' ', '_'))
        url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}'
        data = _api_get(url)

        if data:
            extract = data.get('extract', '')
            page_url = data.get('content_urls', {}).get('desktop', {}).get('page', '')
            if strict_validate_wiki_extract(extract, album):
                return _trim_to_sentences(extract, 700), page_url

        time.sleep(0.3)

        # Then try search API
        search_encoded = urllib.parse.quote(query)
        search_url = (
            f'https://en.wikipedia.org/w/api.php?action=query&list=search'
            f'&srsearch={search_encoded}&format=json&srlimit=3'
        )

        data = _api_get(search_url)
        if not data:
            time.sleep(0.3)
            continue

        results = data.get('query', {}).get('search', [])
        for r in results:
            page_title = r.get('title', '')
            encoded_title = urllib.parse.quote(page_title.replace(' ', '_'))
            summary_url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}'

            summary_data = _api_get(summary_url)
            time.sleep(0.3)

            if not summary_data:
                continue

            extract = summary_data.get('extract', '')
            page_url = summary_data.get('content_urls', {}).get('desktop', {}).get('page', '')

            if strict_validate_wiki_extract(extract, album):
                return _trim_to_sentences(extract, 700), page_url

        time.sleep(0.3)

    return None, None


def generate_description(album, artist_info):
    """Generate description from metadata when all external sources fail."""
    title = album['title']
    artist = album['artist']
    year = album.get('year', '')
    label = album.get('label', 'Unknown')
    genres = album.get('genres', ['jazz'])
    tracks = album.get('keyTracks', [])
    era = album.get('era', '')

    inst = ''
    role = ''
    if artist_info:
        instruments = artist_info.get('instruments', [])
        if instruments:
            inst = instruments[0]
            role = INSTRUMENT_ROLE.get(inst, f'{inst} player')

    pg = genres[0] if genres else 'jazz'
    has_label = label and label != 'Unknown'
    has_tracks = len(tracks) >= 2
    v = _variant(album['id'] + '_biofx', 12)

    sentences = []

    # Opening sentence — varied by hash
    if v == 0 and has_label and role:
        sentences.append(
            f"On {title}, {role} {artist} leads "
            f"{_a_or_an(pg)} {pg} session recorded for {label} in {year}."
        )
    elif v == 1 and has_label:
        sentences.append(
            f"{title} is {_a_or_an(pg)} {pg} album by {artist}, "
            f"recorded for {label} in {year}."
        )
    elif v == 2 and has_label and role:
        sentences.append(
            f"Recorded for {label} in {year}, {title} presents {role} {artist} "
            f"working in {_a_or_an(pg)} {pg} vein."
        )
    elif v == 3 and role:
        sentences.append(
            f"{artist}, {role}, recorded {title} in {year}"
            + (f" for {label}." if has_label else ".")
        )
    elif v == 4 and has_label:
        sentences.append(
            f"A {year} {label} date, {title} finds {artist} "
            f"in {_a_or_an(pg)} {pg} setting."
        )
    elif v == 5 and role:
        sentences.append(
            f"{role.capitalize()} {artist}'s {year} album {title} "
            f"draws from the {pg} tradition"
            + (f", released on {label}." if has_label else ".")
        )
    elif v == 6 and has_label:
        sentences.append(
            f"{label} released {title} in {year}, {_a_or_an(pg)} {pg} date led by {artist}."
        )
    elif v == 7:
        sentences.append(
            f"{title} ({year}) captures {artist} exploring {pg} territory"
            + (f" on the {label} label." if has_label else ".")
        )
    elif v == 8 and has_label and role:
        sentences.append(
            f"A {pg} outing from {year}, {title} features {role} {artist} "
            f"recording for {label}."
        )
    elif v == 9 and role:
        sentences.append(
            f"With {title} ({year}), {role} {artist} delivers "
            f"{_a_or_an(pg)} {pg} program"
            + (f" for the {label} label." if has_label else ".")
        )
    elif v == 10 and has_label:
        sentences.append(
            f"{artist}'s {title}, released on {label} in {year}, "
            f"is {_a_or_an(pg)} {pg} recording."
        )
    else:
        sentences.append(
            f"{title} is {_a_or_an(pg)} {pg} album by {artist}"
            + (f", released on {label} in {year}." if has_label else f" from {year}.")
        )

    # Second sentence: tracks or genre detail
    v2 = _variant(album['id'] + '_biofx_s2', 8)

    if has_tracks and v2 < 3:
        track_str = _format_tracks(tracks[:3])
        phrases = [
            f"The program includes {track_str}.",
            f"Highlights of the session include {track_str}.",
            f"The set features {track_str} among its selections.",
        ]
        sentences.append(phrases[v2])
    elif len(genres) > 1 and v2 < 6:
        genres_str = ' and '.join(genres[:2])
        sentences.append(f"The music draws on {genres_str} influences.")
    elif has_tracks:
        track_str = _format_tracks(tracks[:2])
        phrases = [
            f"Among the tracks are {track_str}.",
            f"The date includes {track_str}.",
            f"Standouts include {track_str}.",
        ]
        sentences.append(phrases[v2 % 3])

    # Optional third sentence: label or era context
    v3 = _variant(album['id'] + '_biofx_s3', 6)
    current_len = len(' '.join(sentences))

    if current_len < 200:
        label_ctx = LABEL_CONTEXT.get(label)
        era_ctx = ERA_CONTEXT.get(era)
        if label_ctx and v3 < 2:
            sentences.append(label_ctx)
        elif era_ctx and v3 < 4:
            sentences.append(f"The album comes from {era_ctx}.")

    result = ' '.join(sentences)

    # Safety check against formulaic phrases
    if is_formulaic(result, BANNED_DESC_PHRASES):
        result = (
            f"{title} is {_a_or_an(pg)} {pg} album by {artist}"
            + (f", released on {label} in {year}." if has_label else f" from {year}.")
        )
        if has_tracks:
            result += f" The set features {_format_tracks(tracks[:3])}."

    return result


def generate_significance(album, artist_info, wiki_text=None):
    """Generate significance text for an album."""
    if wiki_text:
        extracted = extract_significance_from_wiki(wiki_text, album)
        if extracted:
            return extracted

    artist = album['artist']
    year = album.get('year', '')
    label = album.get('label', 'Unknown')
    genres = album.get('genres', ['jazz'])
    era = album.get('era', '')
    tracks = album.get('keyTracks', [])

    pg = genres[0] if genres else 'jazz'
    has_label = label and label != 'Unknown'
    has_tracks = len(tracks) >= 1
    era_name = era.replace('-', ' ') if era else 'jazz'

    role = ''
    if artist_info:
        instruments = artist_info.get('instruments', [])
        if instruments:
            role = INSTRUMENT_ROLE.get(instruments[0], f'{instruments[0]} player')

    v = _variant(album['id'] + '_biofx_sig', 14)
    label_ctx = LABEL_CONTEXT.get(label, '')
    era_ctx = ERA_CONTEXT.get(era, '')

    if v == 0 and label_ctx:
        return f"Part of {label}'s {pg} catalog. {label_ctx}"
    elif v == 1 and era_ctx:
        return f"A {pg} recording from {era_ctx}. {artist} adds a personal voice to the idiom."
    elif v == 2 and has_label and role:
        return (
            f"Documents {role} {artist}'s {pg} work for {label}, "
            f"a {year} session reflecting the {era_name} period."
        )
    elif v == 3 and has_tracks and len(tracks) >= 2:
        return (
            f"Features {_format_tracks(tracks[:2])} in {_a_or_an(pg)} {pg} context, "
            f"highlighting {artist}'s interpretive range."
        )
    elif v == 4 and era_ctx and role:
        return f"Captures {role} {artist} during {era_ctx}."
    elif v == 5 and has_label:
        return (
            f"A {year} {pg} date for {label} that documents "
            f"{artist}'s ongoing work in the idiom."
        )
    elif v == 6 and role:
        return (
            f"{role.capitalize()} {artist}'s {pg} sensibility "
            f"is on display in this {year} session, a document of the {era_name} era."
        )
    elif v == 7 and has_label and era_ctx:
        return (
            f"Released by {label} during {era_ctx}, "
            f"this set captures {artist} in characteristic form."
        )
    elif v == 8 and has_tracks and len(genres) > 1:
        return (
            f"Blends {' and '.join(genres[:2])} on tracks including "
            f"{_format_tracks(tracks[:2])}, reflecting {artist}'s range."
        )
    elif v == 9 and has_label and role:
        return (
            f"A {label} session that documents {role} {artist} "
            f"working through the {pg} vocabulary of the {era_name} period."
        )
    elif v == 10 and era_ctx:
        return (
            f"From {era_ctx}, this album positions {artist} "
            f"within the {pg} conversation of the time."
        )
    elif v == 11 and has_label and has_tracks:
        return (
            f"This {label} date features {_format_tracks(tracks[:1])} "
            f"as part of {artist}'s {pg} output from {year}."
        )
    elif v == 12 and role:
        return (
            f"Captures {role} {artist} in a {year} {pg} setting, "
            f"adding to the recorded documentation of the {era_name} era."
        )
    else:
        return (
            f"A {pg} entry from {year} by {artist}, "
            f"documenting the breadth of the {era_name} period."
        )


SIGNIFICANCE_WORDS = [
    'influence', 'influential', 'acclaim', 'groundbreaking', 'landmark',
    'grammy', 'chart', 'best-selling', 'classic', 'standard', 'iconic',
    'pioneering', 'innovative', 'seminal', 'revolutionary', 'definitive',
    'award', 'recognized', 'celebrated', 'critically', 'unprecedented',
    'first', 'debut', 'breakthrough', 'masterpiece', 'important',
    'billboard', 'poll', 'rated', 'ranked', 'canon',
]


def extract_significance_from_wiki(wiki_text, album):
    if not wiki_text or len(wiki_text) < 100:
        return None

    sentences = re.split(r'(?<=[.!?])\s+', wiki_text)
    if len(sentences) < 2:
        return None

    candidates = sentences[1:]
    scored = []
    for s in candidates:
        if len(s) < 30 or len(s) > 300:
            continue
        lower = s.lower()
        score = sum(1 for w in SIGNIFICANCE_WORDS if w in lower)
        if re.search(r'\d+', s):
            score += 0.5
        if any(w in lower for w in ['billboard', 'grammy', 'poll', 'rated', 'ranked']):
            score += 2
        scored.append((score, s))

    if not scored:
        return None

    scored.sort(key=lambda x: -x[0])
    best_score, best_sentence = scored[0]

    if best_score > 0:
        result = best_sentence
        if len(result) > 250:
            result = _trim_to_sentences(result, 250)
        if not is_formulaic(result, BANNED_SIG_PHRASES):
            return result

    if len(candidates) >= 1 and 50 < len(candidates[0]) < 250:
        if not is_formulaic(candidates[0], BANNED_SIG_PHRASES):
            return candidates[0]

    return None


def main():
    dry_run = '--dry-run' in sys.argv
    skip_wiki = '--skip-wiki' in sys.argv

    with open(ALBUMS_FILE) as f:
        albums = json.load(f)
    with open(ARTISTS_FILE) as f:
        artists = json.load(f)
    artist_map = {a['id']: a for a in artists}

    # Load cache
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        print(f'Loaded cache: {len(cache)} entries')

    # Find albums with artist-bio descriptions
    affected = []
    for a in albums:
        if is_bio_description(a.get('description', '')):
            affected.append(a)

    print(f'\nFound {len(affected)} albums with artist-bio descriptions')

    if not affected:
        print('Nothing to fix!')
        return

    # Phase 1: Try Wikipedia with strict validation
    wiki_found = 0
    generated = 0
    cached_hits = 0

    for i, album in enumerate(affected):
        aid = album['id']
        print(f'  [{i+1}/{len(affected)}] {aid} ({album["artist"]} - {album["title"]})...', end=' ', flush=True)

        # Check cache
        if aid in cache:
            cached_hits += 1
            print(f'CACHED ({cache[aid].get("source", "?")})')
            continue

        if not skip_wiki:
            # Try strict Wikipedia search
            desc, wiki_url = search_wikipedia_strict(album)
            if desc and len(desc) >= 80:
                cache[aid] = {
                    'description': desc,
                    'wikipedia': wiki_url,
                    'source': 'wikipedia-strict',
                }
                wiki_found += 1
                print(f'WIKI ({len(desc)} chars)')

                # Save cache periodically
                if (i + 1) % 10 == 0:
                    with open(CACHE_FILE, 'w') as f:
                        json.dump(cache, f, indent=2, ensure_ascii=False)
                continue

        # Fall back to metadata generation
        artist_info = artist_map.get(album.get('artistId'))
        desc = generate_description(album, artist_info)
        cache[aid] = {
            'description': desc,
            'source': 'generated',
        }
        generated += 1
        print(f'GEN ({len(desc)} chars)')

    # Save cache
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    print(f'\n=== Summary ===')
    print(f'Wikipedia (strict): {wiki_found}')
    print(f'Generated: {generated}')
    print(f'Cached: {cached_hits}')
    print(f'Total in cache: {len(cache)}')

    if dry_run:
        print('\nDry run — not applying changes.')
        return

    # Apply changes to albums.json
    print(f'\nApplying changes to albums.json...')
    changed_desc = 0
    changed_sig = 0

    album_map = {a['id']: a for a in albums}

    for aid, fix in cache.items():
        if aid not in album_map:
            continue
        album = album_map[aid]
        artist_info = artist_map.get(album.get('artistId'))

        new_desc = fix.get('description', '')
        if new_desc and is_bio_description(album.get('description', '')):
            album['description'] = new_desc
            changed_desc += 1

            # Update wikipedia URL if we found one
            wiki_url = fix.get('wikipedia')
            if wiki_url:
                album['wikipedia'] = wiki_url

        # Also fix significance if it's formulaic
        if is_formulaic(album.get('significance', ''), BANNED_SIG_PHRASES):
            wiki_text = new_desc if fix.get('source', '').startswith('wikipedia') else None
            new_sig = generate_significance(album, artist_info, wiki_text)
            if new_sig and not is_formulaic(new_sig, BANNED_SIG_PHRASES):
                album['significance'] = new_sig
                changed_sig += 1

    # Write back
    with open(ALBUMS_FILE, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    print(f'Descriptions replaced: {changed_desc}')
    print(f'Significance replaced: {changed_sig}')
    print(f'Done!')


if __name__ == '__main__':
    main()
