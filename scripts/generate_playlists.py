#!/usr/bin/env python3
"""
AI-curated playlist generator using Claude API.
Reads 1,000 albums from albums.json and asks Claude to curate themed playlists.
Output: src/data/playlists.json

Requires: pip install anthropic
Usage: ANTHROPIC_API_KEY=sk-... python3 scripts/generate_playlists.py
"""
import json
import os
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Missing dependency: pip install anthropic")
    sys.exit(1)

ROOT = Path(__file__).parent.parent
ALBUMS_FILE = ROOT / "src" / "data" / "albums.json"
OUTPUT_FILE = ROOT / "src" / "data" / "playlists.json"

PLAYLIST_THEMES = [
    {
        "id": "morning-jazz",
        "name": "Morning Jazz",
        "mood": "morning",
        "prompt_theme": "bright, energizing, optimistic, flowing — ideal for a morning coffee or commute. Think uptempo swing, breezy cool jazz, melodic post-bop.",
    },
    {
        "id": "sunday-afternoon",
        "name": "Sunday Afternoon",
        "mood": "afternoon",
        "prompt_theme": "relaxed, warm, accessible — the kind of music you play on a slow Sunday afternoon. Mix of lyrical ballads, easy swing, and gentle bossa nova-influenced jazz.",
    },
    {
        "id": "evening-wind-down",
        "name": "Evening Wind Down",
        "mood": "evening",
        "prompt_theme": "cool, introspective, intimate — perfect for the hour before dinner or unwinding after work. Slower tempos, rich harmonies, reflective mood.",
    },
    {
        "id": "late-night",
        "name": "Late Night",
        "mood": "night",
        "prompt_theme": "dark, atmospheric, searching — smoky late-night club energy. Free jazz, noir ballads, sparse piano, extended improvisations.",
    },
    {
        "id": "first-listen",
        "name": "First Listen",
        "mood": "gateway",
        "prompt_theme": "the perfect introduction to jazz for someone new. Accessible, iconic, immediately appealing albums that represent the best of the genre without being intimidating.",
    },
    {
        "id": "deep-focus",
        "name": "Deep Focus",
        "mood": "cerebral",
        "prompt_theme": "complex, intellectually engaging — for deep listening sessions. Modal jazz, intricate bebop, avant-garde works that reward close attention.",
    },
    {
        "id": "heartbreak-and-blue",
        "name": "Heartbreak & Blue",
        "mood": "melancholy",
        "prompt_theme": "melancholy, emotionally raw, tender — ballads and blues-inflected albums about loss, longing, and vulnerability.",
    },
    {
        "id": "joy-ride",
        "name": "Joy Ride",
        "mood": "joyful",
        "prompt_theme": "jubilant, exuberant, swinging — pure joy and vitality. Hard-driving swing, celebratory hard bop, funky soul jazz.",
    },
    {
        "id": "nyc-sound",
        "name": "NYC Sound",
        "mood": "urban",
        "prompt_theme": "quintessential New York jazz — the Blue Note sound, Village Vanguard sessions, the gritty energy of 1950s-60s Manhattan clubs. Hard bop, post-bop.",
    },
    {
        "id": "paris-sessions",
        "name": "Paris Sessions",
        "mood": "european",
        "prompt_theme": "cool, refined, European sensibility — jazz recorded in or influenced by Paris and the European scene. ECM aesthetic, cool jazz, chamber jazz.",
    },
    {
        "id": "spirit-and-soul",
        "name": "Spirit & Soul",
        "mood": "spiritual",
        "prompt_theme": "spiritual, searching, transcendent — albums with a sense of reaching beyond. Free jazz, Coltrane-influenced spirituality, soul jazz gospel energy.",
    },
    {
        "id": "electric-era",
        "name": "Electric Era",
        "mood": "fusion",
        "prompt_theme": "electric, funky, boundary-crossing — jazz fusion at its best. Miles Davis electric period, Weather Report, Return to Forever, Mahavishnu Orchestra.",
    },
]


def build_album_catalog(albums: list[dict]) -> str:
    """Build a compact catalog string for the Claude prompt."""
    lines = []
    for a in albums:
        year = a.get("year") or "?"
        genres = ", ".join(a.get("genres", [])[:2])
        lines.append(f'- id: "{a["id"]}" | {a["title"]} by {a["artist"]} ({year}) | {genres}')
    return "\n".join(lines)


def generate_playlist(client: anthropic.Anthropic, theme: dict, catalog: str, album_ids: set[str]) -> dict:
    print(f"  Generating: {theme['name']}...")

    prompt = f"""You are a jazz curator. From the album catalog below, select 12-15 albums for a themed playlist.

THEME: "{theme['name']}"
CHARACTER: {theme['prompt_theme']}

INSTRUCTIONS:
- Choose albums that genuinely fit the theme's character and mood
- Prefer variety in era and artist (avoid picking 3 albums by same artist)
- Order them for best listening flow
- Return ONLY valid JSON, no explanation

RESPONSE FORMAT:
{{
  "albums": ["album-id-1", "album-id-2", ...],
  "description": "2-3 sentence evocative description of this playlist",
  "tags": ["tag1", "tag2"]
}}

Tags should be 1-3 short descriptive words (e.g., "mellow", "classic", "late-night", "essential", "deep-cuts").

ALBUM CATALOG:
{catalog}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Extract JSON if wrapped in code block
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    data = json.loads(raw)

    # Validate album IDs
    valid_albums = [aid for aid in data["albums"] if aid in album_ids]
    invalid = [aid for aid in data["albums"] if aid not in album_ids]
    if invalid:
        print(f"    Warning: {len(invalid)} invalid IDs removed: {invalid[:3]}")

    return {
        "id": theme["id"],
        "name": theme["name"],
        "mood": theme["mood"],
        "description": data["description"],
        "tags": data.get("tags", [])[:3],
        "albums": valid_albums,
        "coverAlbumId": valid_albums[0] if valid_albums else "",
    }


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    with open(ALBUMS_FILE) as f:
        albums: list[dict] = json.load(f)

    album_ids = {a["id"] for a in albums}
    catalog = build_album_catalog(albums)

    print(f"Loaded {len(albums)} albums. Generating {len(PLAYLIST_THEMES)} playlists...")

    client = anthropic.Anthropic(api_key=api_key)
    playlists = []

    for theme in PLAYLIST_THEMES:
        try:
            playlist = generate_playlist(client, theme, catalog, album_ids)
            playlists.append(playlist)
            print(f"    Done: {len(playlist['albums'])} albums, tags: {playlist['tags']}")
        except Exception as e:
            print(f"    Error generating {theme['name']}: {e}")

    OUTPUT_FILE.write_text(json.dumps(playlists, indent=2, ensure_ascii=False))
    print(f"\nWritten {len(playlists)} playlists to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
