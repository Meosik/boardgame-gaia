#!/usr/bin/env python3
"""Normalize all faction-board redraws to the original physical canvas.

Generated PNGs contain different transparent padding and slightly different
canvas ratios.  Cropping only their visible board bounds and fitting them to
the original 2323x1489 scan coordinate system lets one measured structure-slot
map work on every faction face and at every CSS zoom level.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image


TARGET_SIZE = (2323, 1489)
ALPHA_THRESHOLD = 128


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=project_root / "src/assets/faction_boards",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "src/assets/faction_boards/normalized",
    )
    return parser.parse_args()


def opaque_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A").point(
        lambda value: 255 if value >= ALPHA_THRESHOLD else 0
    )
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("faction board has no visible pixels")
    return bbox


def clear_transparent_rgb(image: Image.Image) -> None:
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                pixels[x, y] = (0, 0, 0, 0)


def normalize(source: Path) -> Image.Image:
    image = Image.open(source).convert("RGBA")
    bounds = opaque_bbox(image)
    cropped = image.crop(bounds)
    normalized = cropped.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    alpha = (
        cropped.getchannel("A")
        .point(lambda value: 255 if value >= ALPHA_THRESHOLD else 0)
        .resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    )
    normalized.putalpha(alpha)
    clear_transparent_rgb(normalized)
    return normalized


def main() -> None:
    args = parse_args()
    sources = sorted(args.source_dir.glob("*.png"))
    if len(sources) != 18:
        raise ValueError(f"expected 18 faction-board faces, found {len(sources)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for source in sources:
        output = args.output_dir / f"{source.stem}.webp"
        temporary = output.with_suffix(".tmp.webp")
        image = normalize(source)
        image.save(temporary, format="WEBP", quality=100, method=4, exact=True)
        os.replace(temporary, output)
        print(f"{source.name} -> {output.name}: {image.width}x{image.height} RGBA")


if __name__ == "__main__":
    main()
