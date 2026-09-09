#!/usr/bin/env python3
"""Install reviewed High Fidelity space-sector renders for the frontend.

The reviewed 5200x5640 PNG files remain the lossless masters. Runtime assets
are downsampled to 2600x2820 and encoded as high-quality WebP so the browser
does not download or decode the full 8x-original canvases.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image


SECTOR_IDS = range(1, 11)
SOURCE_SIZE = (5200, 5640)
OUTPUT_SIZE = (2600, 2820)


def parse_args() -> argparse.Namespace:
    frontend_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=(
            frontend_dir
            / "src/assets/space_sectors/upscayl_png_high-fidelity-4x_4x"
        ),
        help="Directory containing reviewed High Fidelity NN.png masters.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=frontend_dir / "src/assets/space_sectors/normalized",
        help="Directory for runtime NN.webp assets.",
    )
    return parser.parse_args()


def normalize_sector(source_path: Path) -> Image.Image:
    with Image.open(source_path) as opened:
        opened.load()
        if opened.size != SOURCE_SIZE:
            raise ValueError(
                f"{source_path.name}: expected {SOURCE_SIZE}, found {opened.size}"
            )
        if opened.mode != "RGBA":
            raise ValueError(
                f"{source_path.name}: expected RGBA, found {opened.mode}"
            )

        return opened.resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    temporary_outputs: list[tuple[Path, Path]] = []

    try:
        for sector_id in SECTOR_IDS:
            stem = f"{sector_id:02d}"
            source_path = args.source_dir / f"{stem}.png"
            if not source_path.is_file():
                raise FileNotFoundError(source_path)

            output_path = args.output_dir / f"{stem}.webp"
            temporary_path = output_path.with_suffix(".tmp.webp")
            normalized = normalize_sector(source_path)
            normalized.save(
                temporary_path,
                format="WEBP",
                quality=92,
                method=6,
                exact=True,
            )
            temporary_outputs.append((temporary_path, output_path))
            print(
                f"{stem}: {source_path.name} {SOURCE_SIZE[0]}x{SOURCE_SIZE[1]}"
                f" -> {output_path.name} {OUTPUT_SIZE[0]}x{OUTPUT_SIZE[1]} RGBA"
            )

        for temporary_path, output_path in temporary_outputs:
            os.replace(temporary_path, output_path)
    finally:
        for temporary_path, _ in temporary_outputs:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
