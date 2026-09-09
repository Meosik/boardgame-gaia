#!/usr/bin/env python3
"""Prepare clean, consistently oriented booster and tech-tile upscale inputs.

The 1024x1024 source captures include neighboring board material and have
non-physical aspect ratios.  This script performs deterministic crop, rotate,
resize, and geometric alpha masking only.  It does not sharpen, recolor, or
invent artwork.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


BOOSTER_SIZE = (360, 1052)
# Exact 4x multiples of the physical frontend slot coordinate systems.
# Standard tiles are shared by the research track and spaceship boards.
STANDARD_TECH_SIZE = (178 * 4, 134 * 4)
ADVANCED_TECH_SIZE = (167 * 4, 132 * 4)


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            Path(__file__).resolve().parents[2]
            / ".omh/archive/gaia_download_sources_2026-09-02/upscale_work/tile_inputs"
        ),
    )
    parser.add_argument(
        "--asset-dir",
        type=Path,
        default=project_root / "src/assets",
    )
    return parser.parse_args()


def numeric_id(path: Path) -> int:
    match = re.search(r"_(\d{2})_", path.name)
    if not match:
        raise ValueError(f"file has no two-digit asset id: {path}")
    return int(match.group(1))


def polygon_mask(size: tuple[int, int], points: list[tuple[float, float]]) -> Image.Image:
    width, height = size
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(
        [(round(x * width), round(y * height)) for x, y in points],
        fill=255,
    )
    return mask


def physical_slot_mask(reference_name: str, size: tuple[int, int]) -> Image.Image:
    """Scale an original cutout silhouette without carrying its edge fringe."""
    project_root = Path(__file__).resolve().parents[1]
    reference = (
        Image.open(project_root / "public/assets/gaiaproject" / reference_name)
        .convert("RGBA")
        .getchannel("A")
        .point(lambda alpha: 255 if alpha >= 128 else 0)
        .resize(size, Image.Resampling.LANCZOS)
    )
    # Pull the mask one output pixel inward so white scan background cannot
    # survive as a halo along the diagonal and connector notches.
    return reference.filter(ImageFilter.MinFilter(3))


def apply_mask(image: Image.Image, mask: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    image.putalpha(mask)
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                pixels[x, y] = (0, 0, 0, 0)
    return image


def normalize_booster(source: Path) -> Image.Image:
    # The physical booster occupies the upper 760 rows of every capture.
    # Counter-clockwise rotation places the pass/special half above income,
    # matching the original physical booster orientation.
    image = Image.open(source).convert("RGB").crop((0, 0, 1024, 760))
    image = image.transpose(Image.Transpose.ROTATE_90).resize(
        BOOSTER_SIZE, Image.Resampling.LANCZOS
    )
    # Shared physical booster silhouette: shallow opposing corner chamfers.
    mask = polygon_mask(
        BOOSTER_SIZE,
        [(0.09, 0), (1, 0), (1, 0.91), (0.91, 1), (0, 1), (0, 0.09)],
    )
    return apply_mask(image, mask)


def normalize_standard_tech(source: Path) -> Image.Image:
    # The standard tile is the upper-right pentagon; the rest is board debris.
    # Source captures are 90 degrees clockwise from the physical board slot.
    image = (
        Image.open(source)
        .convert("RGB")
        .crop((285, 15, 1008, 738))
        .transpose(Image.Transpose.ROTATE_90)
        .resize(STANDARD_TECH_SIZE, Image.Resampling.LANCZOS)
    )
    mask = physical_slot_mask("tech_1k1c.png", STANDARD_TECH_SIZE)
    return apply_mask(image, mask)


def normalize_advanced_tech(source: Path) -> Image.Image:
    # The advanced tile fills the upper 760 rows and has one clipped corner.
    # It has the same clockwise source rotation as the standard tiles.
    image = (
        Image.open(source)
        .convert("RGB")
        .crop((0, 13, 1024, 760))
        .transpose(Image.Transpose.ROTATE_90)
        .resize(ADVANCED_TECH_SIZE, Image.Resampling.LANCZOS)
    )
    mask = physical_slot_mask("adv_trade.png", ADVANCED_TECH_SIZE)
    return apply_mask(image, mask)


def save_group(
    sources: list[Path],
    output_dir: Path,
    prefix: str,
    normalizer,
    id_offset: int = 0,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for source in sources:
        tile_id = numeric_id(source) + id_offset
        output = output_dir / f"{prefix}_{tile_id:02d}.png"
        image = normalizer(source)
        image.save(output, format="PNG", optimize=True)
        print(f"{prefix}_{tile_id:02d}: {source.name} -> {output} ({image.width}x{image.height})")


def main() -> None:
    args = parse_args()
    boosters = sorted((args.asset_dir / "round_boosters").glob("booster_*.jpg"))
    standard = sorted((args.asset_dir / "tech_tiles/standard").glob("tech_std_*.jpg"))
    advanced = sorted((args.asset_dir / "tech_tiles/advanced").glob("tech_adv_*.jpg"))
    lost_fleet = sorted((args.asset_dir / "tech_tiles/lost_fleet").glob("tech_lf_*.jpg"))

    save_group(boosters, args.output_dir / "round_boosters", "booster", normalize_booster)
    save_group(standard, args.output_dir / "tech_tiles/standard", "std", normalize_standard_tech)
    save_group(
        lost_fleet,
        args.output_dir / "tech_tiles/standard",
        "std",
        normalize_standard_tech,
        id_offset=10,
    )
    save_group(advanced, args.output_dir / "tech_tiles/advanced", "adv", normalize_advanced_tech)


if __name__ == "__main__":
    main()
