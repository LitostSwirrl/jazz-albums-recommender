#!/usr/bin/env python3
"""
Rewrite formulaic album descriptions and significance texts in albums.json.

Sources (priority order):
1. Wikipedia REST API — for albums with existing wikipedia URL
2. Wikipedia search API — discover pages for albums without URL
3. MusicBrainz API — find Wikipedia URLs via release-group URL relationships
4. Metadata generation — last resort, uses album data + embedded jazz knowledge

Usage:
    python3 scripts/rewrite_descriptions.py             # Full run (fetch + apply)
    python3 scripts/rewrite_descriptions.py --dry-run    # Show what would change
    python3 scripts/rewrite_descriptions.py --stats      # Show current stats only
    python3 scripts/rewrite_descriptions.py --apply-only # Skip fetching, apply cache

Cache: /tmp/wiki_descriptions_cache.json
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

# ── Configuration ──────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, '..', 'src', 'data')
ALBUMS_FILE = os.path.join(DATA_DIR, 'albums.json')
ARTISTS_FILE = os.path.join(DATA_DIR, 'artists.json')
CACHE_FILE = '/tmp/wiki_descriptions_cache.json'

HEADERS = {
    'User-Agent': 'JazzAlbumsRecommender/2.0 (educational; github.com/LitostSwirrl)',
    'Accept': 'application/json',
}

RATE_LIMIT_WIKI = 0.25
RATE_LIMIT_MB = 1.1
MAX_DESC_LENGTH = 700
MIN_DESC_LENGTH = 80

# ── Banned Formulaic Phrases ──────────────────────────────────────────
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

# ── Jazz Knowledge Database ──────────────────────────────────────────
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
    'Steeplechase': 'The Danish Steeplechase label documented American jazz musicians recording in Copenhagen.',
    'Black Saint': 'The Italian Black Saint label supported the jazz avant-garde from the 1970s onward.',
    'Soul Note': "Soul Note, Black Saint's sister label, documented creative jazz musicians from the 1970s onward.",
    'Debut': "Charles Mingus and Max Roach's Debut Records was one of the first musician-owned jazz labels.",
    'Savoy': "Savoy Records documented early bebop, including Charlie Parker's landmark sessions.",
    'Dial': "Dial Records captured some of Charlie Parker's most inspired West Coast recordings.",
    'Bethlehem Records': 'Bethlehem Records was an independent 1950s label, home to early Nina Simone and Chris Connor.',
    'Milestone': 'Milestone Records documented McCoy Tyner and other post-bop musicians.',
    'Enja': 'The German Enja label documented American and European creative jazz.',
    'Nonesuch': 'Nonesuch Records bridged jazz, world music, and classical.',
    'Warner Bros. Records': 'Warner Bros. gave jazz artists commercial reach and creative freedom.',
    'Candid': 'Candid Records, briefly run by Nat Hentoff, captured politically charged jazz in the early 1960s.',
    'Okeh': 'Okeh Records was a pioneering label that documented early jazz and blues.',
    'Decca Records': 'Decca Records captured swing era big bands and early jazz vocalists.',
    'Vogue': 'The French Vogue label documented Django Reinhardt and the European jazz scene.',
    'Incus': "Derek Bailey and Evan Parker's Incus label was dedicated to free improvisation.",
    'Pi Recordings': 'Pi Recordings documents the contemporary jazz avant-garde.',
    'Clean Feed': 'The Portuguese Clean Feed label is a leading outlet for contemporary creative jazz.',
    'Tzadik': "John Zorn's Tzadik label spans the avant-garde from jazz to experimental music.",
    'Muse': 'Muse Records provided a home for mainstream jazz in the 1970s and 80s.',
    'GRP': 'GRP Records was a leading smooth and contemporary jazz label in the 1980s and 90s.',
    'Arista': 'Arista Records under Clive Davis supported jazz alongside its pop and rock catalog.',
    'Asch': 'Asch Records, precursor to Folkways, documented folk, jazz, and world music.',
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

SIGNIFICANCE_WORDS = [
    'influence', 'influential', 'acclaim', 'groundbreaking', 'landmark',
    'grammy', 'chart', 'best-selling', 'classic', 'standard', 'iconic',
    'pioneering', 'innovative', 'seminal', 'revolutionary', 'definitive',
    'award', 'recognized', 'celebrated', 'critically', 'unprecedented',
    'first', 'debut', 'breakthrough', 'masterpiece', 'important',
    'billboard', 'poll', 'rated', 'ranked', 'canon',
]

BAD_WIKI_INDICATORS = [
    'may refer to', 'disambiguation', 'is a list of', 'discography of',
    'may also refer to', 'is the discography',
]

MUSIC_INDICATORS = [
    'album', 'jazz', 'record', 'music', 'recording', 'studio',
    'released', 'label', 'tracks', 'composed', 'musician',
    'saxophone', 'trumpet', 'piano', 'bass', 'drums', 'guitar',
    'quintet', 'quartet', 'trio', 'ensemble', 'orchestra',
    'bebop', 'swing', 'fusion', 'bop', 'improvisation',
    'vibraphone', 'trombone', 'vocals', 'singer', 'organ',
    'flute', 'clarinet', 'cornet', 'percussion',
]


# ── Utility Functions ──────────────────────────────────────────────────

def _variant(seed, n):
    """Deterministic variant selector using MD5 hash."""
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return h % n


def _api_get(url, timeout=15):
    """HTTP GET with retry."""
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
    """Trim text to sentence boundary within max_len."""
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
    """Format track list naturally."""
    quoted = [f'"{t}"' for t in tracks]
    if len(quoted) == 1:
        return quoted[0]
    if len(quoted) == 2:
        return f'{quoted[0]} and {quoted[1]}'
    return ', '.join(quoted[:-1]) + f', and {quoted[-1]}'


def _a_or_an(word):
    """Return 'a' or 'an' based on word."""
    if not word:
        return 'a'
    return 'an' if word[0].lower() in 'aeiou' else 'a'


def _save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


# ── Detection Functions ──────────────────────────────────────────────

def is_formulaic_desc(text):
    """Check if description uses formulaic template language."""
    if not text:
        return True
    lower = text.lower()
    for phrase in BANNED_DESC_PHRASES:
        if re.search(phrase.lower(), lower):
            return True
    return False


def is_formulaic_sig(text):
    """Check if significance uses formulaic template language."""
    if not text:
        return True
    lower = text.lower()
    for phrase in BANNED_SIG_PHRASES:
        if re.search(phrase.lower(), lower):
            return True
    return False


def has_wrong_content(desc, album):
    """Check if description is about a different album/artist."""
    if not desc or len(desc) < 150:
        return False
    if album.get('artistId') == 'various-artists':
        return False

    artist = album['artist']
    artist_lower = artist.lower()
    desc_lower = desc.lower()
    artist_parts = [p for p in artist_lower.split() if len(p) > 2]

    # Check if our artist is mentioned
    if any(p in desc_lower for p in artist_parts):
        return False

    # Our artist NOT mentioned. Check if someone else IS.
    other_names = re.findall(
        r'(?:by|of)\s+(?:\w+\s+)*([A-Z][\w.]+ [A-Z][a-z]+)', desc
    )
    possessives = re.findall(r'([A-Z][\w.]+ [A-Z][a-z]+)\'s', desc)
    all_names = other_names + possessives

    for name in all_names:
        name_parts = {p.lower() for p in name.split() if len(p) > 2}
        if not name_parts & set(artist_parts):
            return True

    return False


# ── Wikipedia Functions ──────────────────────────────────────────────

def validate_wiki_extract(extract, album):
    """Strict validation of Wikipedia extract."""
    if not extract or len(extract) < 50:
        return False

    lower = extract.lower()

    for bad in BAD_WIKI_INDICATORS:
        if bad in lower:
            return False

    if not any(w in lower for w in MUSIC_INDICATORS):
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

    # Year check
    album_year = album.get('year')
    if album_year:
        years_in_text = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', extract)
        if years_in_text:
            closest = min(abs(int(y) - album_year) for y in years_in_text)
            if closest > 10:
                return False

    return True


def fetch_wiki_from_url(wiki_url):
    """Fetch Wikipedia summary from a known URL."""
    parts = wiki_url.rstrip('/').split('/')
    title = parts[-1]
    api_url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{title}'
    data = _api_get(api_url)
    if not data:
        return None, None
    extract = data.get('extract', '')
    page_url = data.get('content_urls', {}).get('desktop', {}).get('page', wiki_url)
    return extract, page_url


def search_wikipedia(album):
    """Search Wikipedia for an album page. Returns (extract, page_url) or (None, None)."""
    title = album['title']
    artist = album['artist']
    clean_title = re.sub(r'\s*\(.*?\)', '', title).strip()

    queries = [
        f'{clean_title} {artist} album',
        f'{clean_title} album',
    ]

    for query in queries:
        encoded = urllib.parse.quote(query)
        url = (
            f'https://en.wikipedia.org/w/api.php?action=query&list=search'
            f'&srsearch={encoded}&format=json&srlimit=3'
        )

        data = _api_get(url)
        if not data:
            time.sleep(RATE_LIMIT_WIKI)
            continue

        results = data.get('query', {}).get('search', [])

        for r in results:
            page_title = r.get('title', '')
            encoded_title = urllib.parse.quote(page_title.replace(' ', '_'))
            summary_url = f'https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}'

            summary_data = _api_get(summary_url)
            time.sleep(RATE_LIMIT_WIKI)

            if not summary_data:
                continue

            extract = summary_data.get('extract', '')
            page_url = summary_data.get('content_urls', {}).get('desktop', {}).get('page', '')

            if validate_wiki_extract(extract, album):
                return extract, page_url

        time.sleep(RATE_LIMIT_WIKI)

    return None, None


# ── MusicBrainz Functions ────────────────────────────────────────────

def search_musicbrainz_for_wiki(album):
    """Search MusicBrainz for a release-group and find its Wikipedia URL."""
    title = album['title']
    artist = album['artist']
    clean_title = re.sub(r'\s*\(.*?\)', '', title).strip()
    query = urllib.parse.quote(f'releasegroup:"{clean_title}" AND artist:"{artist}"')
    url = f'https://musicbrainz.org/ws/2/release-group/?query={query}&fmt=json&limit=3'

    data = _api_get(url)
    if not data:
        return None

    release_groups = data.get('release-groups', [])

    for rg in release_groups:
        mbid = rg.get('id')
        if not mbid:
            continue

        rg_title = rg.get('title', '').lower()
        if clean_title.lower() not in rg_title and rg_title not in clean_title.lower():
            continue

        time.sleep(RATE_LIMIT_MB)
        rel_url = f'https://musicbrainz.org/ws/2/release-group/{mbid}?inc=url-rels&fmt=json'
        rel_data = _api_get(rel_url)
        if not rel_data:
            continue

        for rel in rel_data.get('relations', []):
            if rel.get('type') == 'wikipedia':
                wiki_url = rel.get('url', {}).get('resource', '')
                if 'en.wikipedia.org' in wiki_url:
                    return wiki_url

    return None


# ── Description Generation (last resort) ─────────────────────────────

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
    v = _variant(album['id'], 12)

    sentences = []

    # ── Opening sentence ──
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

    # ── Second sentence: tracks or genre detail ──
    v2 = _variant(album['id'] + '_s2', 8)

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

    # ── Optional third sentence: label or era context ──
    v3 = _variant(album['id'] + '_s3', 6)
    current_len = len(' '.join(sentences))

    if current_len < 200:
        label_ctx = LABEL_CONTEXT.get(label)
        era_ctx = ERA_CONTEXT.get(era)
        if label_ctx and v3 < 2:
            sentences.append(label_ctx)
        elif era_ctx and v3 < 4:
            sentences.append(f"The album comes from {era_ctx}.")

    result = ' '.join(sentences)

    # Safety check
    if is_formulaic_desc(result):
        result = (
            f"{title} is {_a_or_an(pg)} {pg} album by {artist}"
            + (f", released on {label} in {year}." if has_label else f" from {year}.")
        )
        if has_tracks:
            result += f" The set features {_format_tracks(tracks[:3])}."

    return result


# ── Significance Generation ──────────────────────────────────────────

def extract_significance_from_wiki(wiki_text, album):
    """Try to extract a significance-worthy sentence from Wikipedia text."""
    if not wiki_text or len(wiki_text) < 100:
        return None

    sentences = re.split(r'(?<=[.!?])\s+', wiki_text)
    if len(sentences) < 2:
        return None

    # Skip opening sentence
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
        # Make sure extracted text isn't itself formulaic
        if not is_formulaic_sig(result):
            return result

    # Fallback: use second sentence if informative enough
    if len(candidates) >= 1 and 50 < len(candidates[0]) < 250:
        if not is_formulaic_sig(candidates[0]):
            return candidates[0]

    return None


def generate_significance(album, artist_info, wiki_text=None):
    """Generate significance text for an album."""
    # Try Wikipedia extraction first
    if wiki_text:
        extracted = extract_significance_from_wiki(wiki_text, album)
        if extracted:
            return extracted

    # Generate from metadata
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

    v = _variant(album['id'] + '_sig', 14)
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


# ── Main Pipeline ────────────────────────────────────────────────────

def main():
    dry_run = '--dry-run' in sys.argv
    stats_only = '--stats' in sys.argv
    apply_only = '--apply-only' in sys.argv

    # Load data
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

    # ── Phase 0: Classify albums ──
    formulaic_desc = []
    wrong_desc = []
    formulaic_sig = []
    good_desc_count = 0
    good_sig_count = 0

    for album in albums:
        desc = album.get('description', '')
        sig = album.get('significance', '')

        if has_wrong_content(desc, album):
            wrong_desc.append(album)
        elif is_formulaic_desc(desc):
            formulaic_desc.append(album)
        else:
            good_desc_count += 1

        if is_formulaic_sig(sig):
            formulaic_sig.append(album)
        else:
            good_sig_count += 1

    need_desc = formulaic_desc + wrong_desc
    need_sig = formulaic_sig

    print(f'\n=== Classification ===')
    print(f'Total albums: {len(albums)}')
    print(f'Formulaic descriptions: {len(formulaic_desc)}')
    print(f'Wrong descriptions: {len(wrong_desc)}')
    print(f'Good descriptions: {good_desc_count}')
    print(f'Formulaic significance: {len(formulaic_sig)}')
    print(f'Good significance: {good_sig_count}')
    print(f'Need description fix: {len(need_desc)}')
    print(f'Need significance fix: {len(need_sig)}')

    if stats_only:
        return

    if not apply_only:
        # ── Phase 1: Wikipedia from existing URL ──
        print(f'\n=== Phase 1: Wikipedia from URL ===')
        wiki_fetched = 0
        wiki_failed = 0
        phase1_albums = [a for a in need_desc if a.get('wikipedia')
                         and (a['id'] not in cache or not cache[a['id']].get('description'))]

        for i, album in enumerate(phase1_albums):
            aid = album['id']
            print(f'  [{i+1}/{len(phase1_albums)}] {aid}...', end=' ', flush=True)

            extract, page_url = fetch_wiki_from_url(album['wikipedia'])

            if extract and validate_wiki_extract(extract, album):
                trimmed = _trim_to_sentences(extract, MAX_DESC_LENGTH)
                cache[aid] = {
                    'description': trimmed,
                    'wiki_text': extract,
                    'wikipedia': page_url or album['wikipedia'],
                    'source': 'wikipedia-url',
                }
                wiki_fetched += 1
                print(f'OK ({len(trimmed)} chars)')
            else:
                wiki_failed += 1
                print('FAILED')

            time.sleep(RATE_LIMIT_WIKI)
            if (i + 1) % 20 == 0:
                _save_cache(cache)

        _save_cache(cache)
        print(f'  Result: {wiki_fetched} found, {wiki_failed} failed')

        # ── Phase 2: Wikipedia Search ──
        print(f'\n=== Phase 2: Wikipedia Search ===')
        search_found = 0
        remaining = [a for a in need_desc
                     if a['id'] not in cache or not cache[a['id']].get('description')]
        print(f'  Searching for {len(remaining)} albums...')

        for i, album in enumerate(remaining):
            aid = album['id']
            print(f'  [{i+1}/{len(remaining)}] {aid}...', end=' ', flush=True)

            extract, page_url = search_wikipedia(album)

            if extract and validate_wiki_extract(extract, album):
                trimmed = _trim_to_sentences(extract, MAX_DESC_LENGTH)
                cache[aid] = {
                    'description': trimmed,
                    'wiki_text': extract,
                    'wikipedia': page_url,
                    'source': 'wikipedia-search',
                }
                search_found += 1
                print(f'OK ({len(trimmed)} chars)')
            else:
                print('NOT FOUND')

            time.sleep(RATE_LIMIT_WIKI)
            if (i + 1) % 20 == 0:
                _save_cache(cache)

        _save_cache(cache)
        print(f'  Result: {search_found} found')

        # ── Phase 3: MusicBrainz Discovery ──
        print(f'\n=== Phase 3: MusicBrainz Discovery ===')
        mb_found = 0
        remaining = [a for a in need_desc
                     if a['id'] not in cache or not cache[a['id']].get('description')]
        print(f'  Searching MusicBrainz for {len(remaining)} albums...')

        for i, album in enumerate(remaining):
            aid = album['id']
            print(f'  [{i+1}/{len(remaining)}] {aid}...', end=' ', flush=True)

            wiki_url = search_musicbrainz_for_wiki(album)

            if wiki_url:
                time.sleep(RATE_LIMIT_WIKI)
                extract, page_url = fetch_wiki_from_url(wiki_url)

                if extract and validate_wiki_extract(extract, album):
                    trimmed = _trim_to_sentences(extract, MAX_DESC_LENGTH)
                    cache[aid] = {
                        'description': trimmed,
                        'wiki_text': extract,
                        'wikipedia': page_url or wiki_url,
                        'source': 'musicbrainz-wikipedia',
                    }
                    mb_found += 1
                    print(f'OK ({len(trimmed)} chars)')
                    time.sleep(RATE_LIMIT_MB)
                    if (i + 1) % 10 == 0:
                        _save_cache(cache)
                    continue

            print('NOT FOUND')
            time.sleep(RATE_LIMIT_MB)
            if (i + 1) % 10 == 0:
                _save_cache(cache)

        _save_cache(cache)
        print(f'  Result: {mb_found} found')

    # ── Phase 4: Generate from metadata (last resort) ──
    print(f'\n=== Phase 4: Generate from Metadata ===')
    gen_count = 0
    remaining = [a for a in need_desc
                 if a['id'] not in cache or not cache[a['id']].get('description')]

    for album in remaining:
        aid = album['id']
        artist_info = artist_map.get(album.get('artistId', ''), {})
        desc = generate_description(album, artist_info)
        cache[aid] = cache.get(aid, {})
        cache[aid]['description'] = desc
        cache[aid]['source'] = 'generated'
        gen_count += 1

    print(f'  Generated: {gen_count} descriptions')

    # ── Phase 5: Rewrite significance texts ──
    print(f'\n=== Phase 5: Rewrite Significance ===')
    sig_from_wiki = 0
    sig_generated = 0

    for album in need_sig:
        aid = album['id']
        artist_info = artist_map.get(album.get('artistId', ''), {})

        # Get wiki text if available
        wiki_text = None
        if aid in cache:
            wiki_text = cache[aid].get('wiki_text') or cache[aid].get('description')
        elif not is_formulaic_desc(album.get('description', '')):
            wiki_text = album['description']

        sig = generate_significance(album, artist_info, wiki_text)

        if aid not in cache:
            cache[aid] = {}
        cache[aid]['significance'] = sig

        if wiki_text and extract_significance_from_wiki(wiki_text, album):
            sig_from_wiki += 1
        else:
            sig_generated += 1

    _save_cache(cache)
    print(f'  From Wikipedia text: {sig_from_wiki}')
    print(f'  Generated: {sig_generated}')

    if dry_run:
        print('\n=== DRY RUN — no changes applied ===')
        shown = 0
        for album in albums:
            aid = album['id']
            if aid in cache and shown < 20:
                changes = cache[aid]
                if 'description' in changes or 'significance' in changes:
                    print(f'\n--- {aid} ({album["artist"]}) ---')
                if 'description' in changes:
                    print(f'  OLD DESC: {album["description"][:100]}...')
                    print(f'  NEW DESC: {changes["description"][:100]}...')
                    print(f'  SOURCE: {changes.get("source", "?")}')
                if 'significance' in changes:
                    print(f'  OLD SIG: {album["significance"][:80]}...')
                    print(f'  NEW SIG: {changes["significance"][:80]}...')
                    shown += 1
        return

    # ── Phase 6: Apply changes ──
    print(f'\n=== Phase 6: Apply Changes ===')
    desc_changed = 0
    sig_changed = 0
    wiki_added = 0

    for album in albums:
        aid = album['id']
        if aid not in cache:
            continue

        changes = cache[aid]

        if 'description' in changes:
            new_desc = changes['description']
            if new_desc and new_desc != album.get('description'):
                album['description'] = new_desc
                desc_changed += 1

        if 'significance' in changes:
            new_sig = changes['significance']
            if new_sig and new_sig != album.get('significance'):
                album['significance'] = new_sig
                sig_changed += 1

        if 'wikipedia' in changes and changes['wikipedia']:
            if not album.get('wikipedia'):
                album['wikipedia'] = changes['wikipedia']
                wiki_added += 1

    # ── Phase 7: Validate ──
    print(f'\n=== Phase 7: Validation ===')
    still_bad_desc = 0
    still_bad_sig = 0
    too_short = 0

    for album in albums:
        if is_formulaic_desc(album.get('description', '')):
            still_bad_desc += 1
        if is_formulaic_sig(album.get('significance', '')):
            still_bad_sig += 1
        if len(album.get('description', '')) < MIN_DESC_LENGTH:
            too_short += 1

    print(f'  Still formulaic descriptions: {still_bad_desc}')
    print(f'  Still formulaic significance: {still_bad_sig}')
    print(f'  Too short descriptions: {too_short}')

    if still_bad_desc > 0 or still_bad_sig > 0:
        print(f'\n  WARNING: Some formulaic text remains!')
        for album in albums:
            if is_formulaic_desc(album.get('description', '')):
                print(f'    DESC: {album["id"]}: {album["description"][:80]}...')
                if still_bad_desc > 5:
                    print(f'    ... and {still_bad_desc - 5} more')
                    break
        for album in albums:
            if is_formulaic_sig(album.get('significance', '')):
                print(f'    SIG: {album["id"]}: {album["significance"][:80]}...')
                if still_bad_sig > 5:
                    print(f'    ... and {still_bad_sig - 5} more')
                    break

    # Write output
    with open(ALBUMS_FILE, 'w') as f:
        json.dump(albums, f, indent=2, ensure_ascii=False)

    print(f'\n=== Summary ===')
    print(f'Descriptions changed: {desc_changed}')
    print(f'Significance changed: {sig_changed}')
    print(f'Wikipedia URLs added: {wiki_added}')
    print(f'File written: {ALBUMS_FILE}')


if __name__ == '__main__':
    main()
