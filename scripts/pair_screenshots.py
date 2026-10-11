#!/usr/bin/env python3
"""Composite light/dark screenshot pairs into one image: light left, dark right.

The screenshots in `screenshots/` are built by capturing the *same* page twice — same viewport,
same state, only `dashboard.theme` switched between a light and a dark theme — and then gluing the
two captures together. This script does the gluing.

Expected input file names in --dir (produced by whatever you use to capture):

    <page>-light-<size>.png      e.g. models-light-1280.png
    <page>-dark-<size>.png       e.g. models-dark-1280.png

Output: `<page>-<size>-light-dark.png` in the same directory.

Usage:
    python3 pair_screenshots.py --dir ../../screenshots-captures \\
        --pages models skills chat --sizes 1280 --width 820
"""
from __future__ import annotations

import argparse
import pathlib

from PIL import Image, ImageDraw

LANCZOS = getattr(Image, "Resampling", Image).LANCZOS  # Pillow >= 9.1 moved the constant

MARGIN = 18      # border around the whole composition
GAP = 18         # space between the light and the dark capture
CORNER = 14      # corner radius of each capture
BACKDROP = (203, 207, 214)  # neutral grey that separates the two themes


def rounded(image: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, image.size[0] - 1, image.size[1] - 1], radius=radius, fill=255
    )
    out = Image.new("RGBA", image.size, (0, 0, 0, 0))
    out.paste(image.convert("RGBA"), (0, 0), mask)
    return out


def build(directory: pathlib.Path, page: str, size: str, width: int | None) -> pathlib.Path:
    light = Image.open(directory / f"{page}-light-{size}.png").convert("RGB")
    dark = Image.open(directory / f"{page}-dark-{size}.png").convert("RGB")

    if width:  # scale both to the same target width
        height = int(light.size[1] * width / light.size[0])
        light = light.resize((width, height), LANCZOS)
        dark = dark.resize((width, height), LANCZOS)

    if light.size != dark.size:  # never compare captures of different heights
        height = min(light.size[1], dark.size[1])
        light = light.crop((0, 0, light.size[0], height))
        dark = dark.crop((0, 0, dark.size[0], height))

    w, h = light.size
    canvas = Image.new("RGB", (w * 2 + GAP + MARGIN * 2, h + MARGIN * 2), BACKDROP)
    left, right = rounded(light, CORNER), rounded(dark, CORNER)
    canvas.paste(left, (MARGIN, MARGIN), left)
    canvas.paste(right, (MARGIN + w + GAP, MARGIN), right)

    target = directory / f"{page}-{size}-light-dark.png"
    canvas.save(target)
    return target


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", required=True, type=pathlib.Path)
    ap.add_argument("--pages", nargs="+", required=True)
    ap.add_argument("--sizes", nargs="+", default=["1280"])
    ap.add_argument("--width", type=int, default=None,
                    help="scale both captures to this width before composing")
    args = ap.parse_args()

    for size in args.sizes:
        for page in args.pages:
            try:
                target = build(args.dir, page, size, args.width)
            except FileNotFoundError as missing:
                print(f"skip: {missing}")
                continue
            with Image.open(target) as composed:
                print(f"{target}  {composed.size[0]}x{composed.size[1]}")


if __name__ == "__main__":
    main()
