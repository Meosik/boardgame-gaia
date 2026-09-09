#!/usr/bin/env python3
"""Install reviewed High Fidelity Interspace masters for the frontend.

The large PNG files remain archival masters. Runtime WebP assets use half of
the master dimensions and restore the approved alpha footprint from the
previously normalized PNG source so model-generated edge noise cannot alter
the physical tile geometry.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image


INTERSPACE_IDS = range(1, 8)

INTERSPACE_MASTER_SIZE = (3728, 3728)
INTERSPACE_OUTPUT_SIZE = (1864, 1864)


def parse_args() -> argparse.Namespace:
    frontend_dir = Path(__file__).resolve().parents[1]
    assets_dir = frontend_dir / "src/assets"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--interspace-master-dir",
        type=Path,
        default=(
            assets_dir
            / "interspace_tiles/upscayl_png_high-fidelity-4x_4x"
        ),
    )
    parser.add_argument(
        "--interspace-output-dir",
        type=Path,
        default=assets_dir / "interspace_tiles/normalized",
    )
    return parser.parse_args()


def clean_transparent_pixels(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    visible = alpha.point(lambda value: 255 if value > 0 else 0)
    cleaned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    cleaned.paste(image, mask=visible)
    cleaned.putalpha(alpha)
    return cleaned


def build_runtime_asset(
    master_path: Path,
    reference_path: Path,
    expected_master_size: tuple[int, int],
    output_size: tuple[int, int],
) -> Image.Image:
    with Image.open(master_path) as opened:
        opened.load()
        if opened.size != expected_master_size:
            raise ValueError(
                f"{master_path.name}: expected {expected_master_size}, found {opened.size}"
            )
        if opened.mode != "RGBA":
            raise ValueError(
                f"{master_path.name}: expected RGBA, found {opened.mode}"
            )
        runtime = opened.resize(output_size, Image.Resampling.LANCZOS)

    with Image.open(reference_path) as opened:
        reference_alpha = opened.convert("RGBA").getchannel("A").resize(
            output_size,
            Image.Resampling.LANCZOS,
        )

    runtime.putalpha(reference_alpha)
    return clean_transparent_pixels(runtime)


def save_runtime_asset(image: Image.Image, output_path: Path) -> Path:
    temporary_path = output_path.with_suffix(".tmp.webp")
    image.save(
        temporary_path,
        format="WEBP",
        quality=92,
        method=6,
        exact=True,
    )
    return temporary_path


def main() -> None:
    args = parse_args()
    frontend_dir = Path(__file__).resolve().parents[1]
    assets_dir = frontend_dir / "src/assets"
    args.interspace_output_dir.mkdir(parents=True, exist_ok=True)
    pending: list[tuple[Path, Path]] = []

    try:
        for tile_id in INTERSPACE_IDS:
            stem = f"{tile_id:02d}"
            master_path = args.interspace_master_dir / f"{stem}.png"
            reference_path = assets_dir / f"interspace_tiles/{tile_id}.png"
            output_path = args.interspace_output_dir / f"{stem}.webp"
            runtime = build_runtime_asset(
                master_path,
                reference_path,
                INTERSPACE_MASTER_SIZE,
                INTERSPACE_OUTPUT_SIZE,
            )
            pending.append((save_runtime_asset(runtime, output_path), output_path))
            print(f"Interspace {stem}: {output_path.name} {runtime.size} RGBA")

        for temporary_path, output_path in pending:
            os.replace(temporary_path, output_path)
    finally:
        for temporary_path, _ in pending:
            temporary_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
