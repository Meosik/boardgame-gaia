#!/usr/bin/env python3
"""Install AI-upscaled round boosters on one stable physical footprint.

Generated cutouts preserve the printed artwork but vary slightly in canvas
size and make the tile itself translucent.  This script fits each generated
tile to the exact 2x booster canvas and restores the approved alpha silhouette
from the prepared 360x1052 reference cutout.  It does not rotate or recolor the
artwork.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops


BOOSTER_IDS = range(1, 15)
TARGET_SIZE = (720, 2104)  # 2x the prepared 360x1052 physical tile canvas.
VISIBLE_ALPHA_THRESHOLD = 128


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=(
            Path.home()
            / "다운로드/gaia_upscaled_assets/round_boosters"
        ),
        help="Directory containing NN.png renders.",
    )
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=(
            Path(__file__).resolve().parents[2]
            / ".omh/archive/gaia_download_sources_2026-09-02/upscale_work/tile_inputs/round_boosters"
        ),
        help="Directory containing booster_NN.png alpha references.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            Path(__file__).resolve().parents[1]
            / "src/assets/round_boosters/normalized"
        ),
        help="Directory for normalized lossless WebP assets.",
    )
    return parser.parse_args()


def visible_bounds(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A").point(
        lambda value: 255 if value >= VISIBLE_ALPHA_THRESHOLD else 0
    )
    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError("generated booster has no visible pixels")
    return bounds


def normalize_booster(source: Path, alpha_reference: Path) -> Image.Image:
    generated = Image.open(source).convert("RGBA")
    bounds = visible_bounds(generated)
    cropped = generated.crop(bounds)
    normalized = cropped.resize(
        TARGET_SIZE, Image.Resampling.LANCZOS
    )

    reference_alpha = (
        Image.open(alpha_reference)
        .convert("RGBA")
        .getchannel("A")
        .resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    )
    generated_alpha = (
        cropped.getchannel("A")
        .point(lambda value: 255 if value >= VISIBLE_ALPHA_THRESHOLD else 0)
        .resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    )
    # Some generated corners are cut slightly deeper than the approved mask.
    # Intersect both silhouettes so transparent source pixels can never become
    # opaque black wedges, while the reference still rejects any outer fringe.
    alpha = ImageChops.darker(reference_alpha, generated_alpha)
    normalized.putalpha(alpha)

    # Prevent RGB data outside the physical cutout from producing a fringe
    # when the browser samples the transparent corners.
    pixels = normalized.load()
    for y in range(normalized.height):
        for x in range(normalized.width):
            red, green, blue, pixel_alpha = pixels[x, y]
            if pixel_alpha == 0:
                pixels[x, y] = (0, 0, 0, 0)
            else:
                pixels[x, y] = (red, green, blue, pixel_alpha)

    return normalized


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for booster_id in BOOSTER_IDS:
        stem = f"{booster_id:02d}"
        source = args.source_dir / f"{stem}.png"
        alpha_reference = args.reference_dir / f"booster_{stem}.png"
        if not source.is_file() or not alpha_reference.is_file():
            raise FileNotFoundError(f"missing source pair for round booster {stem}")

        output = args.output_dir / f"booster_{stem}.webp"
        normalized = normalize_booster(source, alpha_reference)
        normalized.save(output, format="WEBP", lossless=True, method=6, exact=True)
        print(
            f"{stem}: {source.name} -> {output} "
            f"({normalized.width}x{normalized.height} RGBA)"
        )


if __name__ == "__main__":
    main()
