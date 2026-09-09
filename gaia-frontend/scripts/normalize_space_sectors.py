#!/usr/bin/env python3
"""Rebuild standard space sectors from one consistent set of source scans.

The source scans all use the same 650x705 canvas. This script deliberately
does not use generative enhancement, histogram matching, contrast changes, or
per-tile cropping: it only performs one deterministic 2x Lanczos resize so the
sector geometry and original colour balance remain consistent.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image


FRONTEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = FRONTEND_DIR.parent
SOURCE_DIR = FRONTEND_DIR / "public/assets/gaiaproject"
OUTPUT_DIR = FRONTEND_DIR / "src/assets/space_sectors"
BACKUP_ROOT = PROJECT_DIR / ".omh/backups/space_sectors"

SOURCE_SIZE = (650, 705)
OUTPUT_SIZE = (1300, 1410)
SOURCE_FILENAMES = {
    1: "map_tile_01.png",
    2: "map_tile_02.png",
    3: "map_tile_03.png",
    4: "map_tile_04.png",
    5: "map_tile_05a.png",
    6: "map_tile_06a.png",
    7: "map_tile_07a.png",
    8: "map_tile_08.png",
    9: "map_tile_09.png",
    10: "map_tile_10.png",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize standard space sectors from the original scans."
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Replace generated assets without backing up their current versions.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def alpha_weighted_luma(image: Image.Image) -> float:
    rgba = image.convert("RGBA")
    weighted_luma = 0.0
    total_alpha = 0
    for red, green, blue, alpha in rgba.getdata():
        if alpha == 0:
            continue
        luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        weighted_luma += luma * alpha
        total_alpha += alpha
    if total_alpha == 0:
        raise ValueError("image has no visible pixels")
    return weighted_luma / total_alpha


def backup_outputs() -> Path | None:
    existing = sorted(
        output_path
        for sector_id in SOURCE_FILENAMES
        if (output_path := OUTPUT_DIR / f"{sector_id:02d}.png").exists()
    )
    if not existing:
        return None

    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUP_ROOT / f"before-original-2x-{timestamp}"
    suffix = 1
    while backup_dir.exists():
        backup_dir = BACKUP_ROOT / f"before-original-2x-{timestamp}-{suffix}"
        suffix += 1

    backup_dir.mkdir(parents=True)
    for source_path in existing:
        shutil.copy2(source_path, backup_dir / source_path.name)
    return backup_dir


def normalize_sector(sector_id: int, source_path: Path, output_path: Path) -> None:
    with Image.open(source_path) as opened:
        opened.load()
        if opened.size != SOURCE_SIZE:
            raise ValueError(
                f"{source_path.name}: expected {SOURCE_SIZE}, found {opened.size}"
            )

        source = opened.convert("RGBA")
        source_luma = alpha_weighted_luma(source)
        output = source.resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
        output_luma = alpha_weighted_luma(output)

        # PNG is lossless. Avoid optimization-dependent encoder differences so
        # repeated runs remain fast and predictable.
        output.save(output_path, "PNG", compress_level=6)

    luma_delta = output_luma - source_luma
    print(
        f"{sector_id:02d}: {source_path.name} {SOURCE_SIZE[0]}x{SOURCE_SIZE[1]}"
        f" -> {output_path.name} {OUTPUT_SIZE[0]}x{OUTPUT_SIZE[1]}"
        f" | luma {source_luma:.4f} -> {output_luma:.4f}"
        f" ({luma_delta:+.4f}) | sha256 {sha256(output_path)[:12]}"
    )


def main() -> None:
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not args.no_backup:
        backup_dir = backup_outputs()
        if backup_dir is not None:
            print(f"backup: {backup_dir.relative_to(PROJECT_DIR)}")

    for sector_id, source_filename in SOURCE_FILENAMES.items():
        source_path = SOURCE_DIR / source_filename
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        normalize_sector(sector_id, source_path, OUTPUT_DIR / f"{sector_id:02d}.png")


if __name__ == "__main__":
    main()
