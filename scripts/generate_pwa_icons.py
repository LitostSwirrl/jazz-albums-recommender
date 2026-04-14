"""Rasterize public/favicon.svg into PWA icon PNGs.

Run once and commit the output. Do NOT wire into CI.
Outputs under public/:
  - icon-192.png         (Android / PWA install, 192x192)
  - icon-512.png         (Android / PWA install, 512x512)
  - apple-touch-icon.png (iOS homescreen, 180x180)
"""

from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "public" / "favicon.svg"
OUT = ROOT / "public"

TARGETS = [
    ("icon-192.png", 192),
    ("icon-512.png", 512),
    ("apple-touch-icon.png", 180),
]


def main() -> None:
    svg_bytes = SRC.read_bytes()
    for name, size in TARGETS:
        dest = OUT / name
        cairosvg.svg2png(
            bytestring=svg_bytes,
            write_to=str(dest),
            output_width=size,
            output_height=size,
        )
        print(f"wrote {dest.relative_to(ROOT)} ({size}x{size})")


if __name__ == "__main__":
    main()
