#!/usr/bin/env python3
"""Normalize generated advanced-tech artwork to the exact app slot geometry."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image


ADVANCED_TILE_IDS = (*range(1, 18), *range(19, 23))
OUTPUT_SIZE = (668, 528)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=(
            Path.home()
            / "다운로드/gaia_upscaled_assets/tech_tiles/advanced"
        ),
        help="Directory containing generated NN.png files.",
    )
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=(
            Path(__file__).resolve().parents[2]
            / ".omh/archive/gaia_download_sources_2026-09-02/upscale_work/tile_inputs/tech_tiles/advanced"
        ),
        help="Directory containing mapped adv_NN.png templates and normalized outputs.",
    )
    return parser.parse_args()


def opaque_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    solid_alpha = alpha.point(lambda value: 255 if value >= 128 else 0)
    bbox = solid_alpha.getbbox()
    if bbox is None:
        raise ValueError("image has no opaque pixels")
    return bbox


def main() -> None:
    args = parse_args()
    normalized: dict[Path, Image.Image] = {}

    for tile_id in ADVANCED_TILE_IDS:
        generated_path = args.source_dir / f"{tile_id:02}.png"
        template_path = args.reference_dir / f"adv_{tile_id:02}.png"
        if not generated_path.exists():
            raise FileNotFoundError(generated_path)
        if not template_path.exists():
            raise FileNotFoundError(template_path)

        generated = Image.open(generated_path).convert("RGBA")
        template = Image.open(template_path).convert("RGBA")
        if template.size != OUTPUT_SIZE:
            raise ValueError(f"{template_path} is {template.size}; expected {OUTPUT_SIZE}")

        # Image generators may add padding or return a 3:2 canvas. Crop only
        # their transparent margin, then restore the known physical slot size.
        artwork = generated.crop(opaque_bbox(generated)).resize(
            OUTPUT_SIZE,
            Image.Resampling.LANCZOS,
        )
        artwork.putalpha(template.getchannel("A"))
        normalized[template_path] = artwork

    # Build every result before replacing any template, preventing partial sets.
    for output_path, image in normalized.items():
        temporary_path = output_path.with_suffix(".tmp.png")
        image.save(temporary_path, format="PNG", optimize=True)
        os.replace(temporary_path, output_path)
        print(f"{output_path.name}: {image.width}x{image.height} RGBA")


if __name__ == "__main__":
    main()
