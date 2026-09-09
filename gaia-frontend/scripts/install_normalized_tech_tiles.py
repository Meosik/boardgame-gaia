#!/usr/bin/env python3
"""Install normalized tech-tile PNGs as lossless frontend WebP assets."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


GROUPS = {
    "standard": ("std", (178, 134)),
    "advanced": ("adv", (167, 132)),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=(
            Path(__file__).resolve().parents[2]
            / ".omh/archive/gaia_download_sources_2026-09-02/upscale_work/tile_inputs/tech_tiles"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "src/assets/tech_tiles/rendered",
    )
    parser.add_argument(
        "--include-advanced",
        action="store_true",
        help="Also install advanced tiles; omitted until their artwork is approved.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    groups = ("standard", "advanced") if args.include_advanced else ("standard",)
    for group in groups:
        prefix, physical_size = GROUPS[group]
        sources = sorted((args.source_dir / group).glob(f"{prefix}_*.png"))
        if not sources:
            raise FileNotFoundError(f"no normalized {group} tech tiles found")

        physical_width, physical_height = physical_size
        for source in sources:
            image = Image.open(source).convert("RGBA")
            if image.width * physical_height != image.height * physical_width:
                raise ValueError(
                    f"{source} is {image.width}x{image.height}; expected {physical_width}:{physical_height}"
                )
            output = args.output_dir / f"{source.stem}.webp"
            image.save(output, format="WEBP", lossless=True, method=6, exact=True)
            print(f"{source.name} -> {output} ({image.width}x{image.height})")


if __name__ == "__main__":
    main()
