#!/usr/bin/env python3
"""Create production WebP derivatives without modifying archival PNG sources."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image


FRONTEND_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = FRONTEND_DIR / "src/assets"

ARTIFACT_SOURCES = {
    artifact_id: f"artifact_{artifact_id:02d}.png"
    for artifact_id in range(1, 14)
}

BOARD_SOURCES = (
    "spaceship_eclipse.png",
    "spaceship_tf_mars.png",
    "spaceship_rebellion.png",
    "spaceship_twilight.png",
    "lost_fleet_tech_requirement_shuttles.png",
    "lost_fleet_tech_requirement_victory_points.png",
    "research_board.png",
    "economy_research_power.png",
    "scoring_board.png",
    "economy_research_victory_points.png",
    "lost_planet.png",
    "terraforming_selection_board.png",
)

BOARD_MAX_SIZES = {
    "lost_fleet_qic_board_overlay.png": (2548, 1048),
}

ICON_SOURCES = ("credits.png", "knowledge.png", "ore.png", "qic.png")
POWER_BADGE_SOURCES = ("power_badge_1.png", "power_badge_3.png", "power_badge_4.png")
ICON_MAX_SIZE = (384, 384)


def clean_transparent_pixels(image: Image.Image) -> Image.Image:
    alpha = image.getchannel("A")
    visible = alpha.point(lambda value: 255 if value > 0 else 0)
    cleaned = Image.new("RGBA", image.size, (0, 0, 0, 0))
    cleaned.paste(image, mask=visible)
    cleaned.putalpha(alpha)
    return cleaned


def convert(source_path: Path, output_path: Path, max_size: tuple[int, int] | None = None) -> None:
    with Image.open(source_path) as opened:
        opened.load()
        image = opened.convert("RGBA" if "A" in opened.getbands() else "RGB")

    if max_size is not None:
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
    if image.mode == "RGBA":
        image = clean_transparent_pixels(image)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".tmp.webp")
    try:
        image.save(
            temporary_path,
            format="WEBP",
            quality=92,
            method=6,
            exact=image.mode == "RGBA",
        )
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    print(
        f"{source_path.relative_to(ASSETS_DIR)} -> "
        f"{output_path.relative_to(ASSETS_DIR)} {image.size} {image.mode}"
    )


def main() -> None:
    artifact_dir = ASSETS_DIR / "artifacts"
    for artifact_id, source_name in ARTIFACT_SOURCES.items():
        convert(
            artifact_dir / source_name,
            artifact_dir / "normalized" / f"artifact_{artifact_id:02d}.webp",
        )

    exploration_dir = ASSETS_DIR / "exploration_boards"
    for source_path in sorted(exploration_dir.glob("*.png")):
        convert(source_path, exploration_dir / "normalized" / f"{source_path.stem}.webp")

    board_dir = ASSETS_DIR / "boards"
    for source_name in BOARD_SOURCES:
        source_path = board_dir / source_name
        convert(source_path, board_dir / "normalized" / f"{source_path.stem}.webp")
    for source_name, max_size in BOARD_MAX_SIZES.items():
        source_path = board_dir / source_name
        convert(
            source_path,
            board_dir / "normalized" / f"{source_path.stem}.webp",
            max_size,
        )

    icon_dir = ASSETS_DIR / "icons"
    for source_name in ICON_SOURCES:
        source_path = icon_dir / source_name
        convert(
            source_path,
            icon_dir / "normalized" / f"{source_path.stem}.webp",
            ICON_MAX_SIZE,
        )
    for source_name in POWER_BADGE_SOURCES:
        source_path = icon_dir / "source" / source_name
        convert(source_path, icon_dir / "normalized" / f"{source_path.stem}.webp")


if __name__ == "__main__":
    main()
