#!/usr/bin/env python3
"""Normalize Deep Space scans to one reproducible tile coordinate system.

The upscaled source files were exported with different canvas sizes and their
three-hex junctions do not sit at the canvas center.  Each source is trimmed to
its visible tile, then stretched on either side of its measured junction so
all generated files share the same outer bounds and junction coordinate.
"""

from pathlib import Path

from PIL import Image


SOURCE_DIR = Path(__file__).resolve().parents[1] / "src/assets/deep_space_sectors"
OUTPUT_DIR = SOURCE_DIR / "normalized"
OUTPUT_SIZE = 1254
TARGET_JUNCTION = (round(OUTPUT_SIZE * 4 / 7), OUTPUT_SIZE // 2)

# Measured where the three printed blue grid lines meet, beneath the sector id.
SOURCE_JUNCTIONS: dict[str, tuple[int, int]] = {
    "11-1.png": (701, 614),
    "11-2.png": (711, 614),
    "12-1.png": (694, 621),
    "12-2.png": (710, 612),
    "13-1.png": (707, 623),
    "13-2.png": (702, 609),
    "14-1.png": (702, 628),
    "14-2.png": (700, 615),
    "15-1.png": (702, 621),
    "15-2.png": (711, 611),
    "16-1.png": (711, 618),
    "16-2.png": (703, 617),
    "17-1.png": (702, 612),
    "17-2.png": (710, 620),
    "18-1.png": (711, 609),
    "18-2.png": (711, 613),
}


def visible_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    thresholded = alpha.point(lambda value: 255 if value >= 64 else 0)
    bbox = thresholded.getbbox()
    if bbox is None:
        raise ValueError("source image has no visible pixels")
    return bbox


def resize_quadrant(
    image: Image.Image,
    source_box: tuple[int, int, int, int],
    target_size: tuple[int, int],
) -> Image.Image:
    return image.crop(source_box).resize(target_size, Image.Resampling.LANCZOS)


def normalize(source_path: Path, junction: tuple[int, int]) -> Path:
    source = Image.open(source_path).convert("RGBA")
    left, top, right, bottom = visible_bbox(source)
    source_x, source_y = junction
    if not (left < source_x < right and top < source_y < bottom):
        raise ValueError(f"{source_path.name}: junction {junction} is outside visible bounds")

    target_x, target_y = TARGET_JUNCTION
    output = Image.new("RGBA", (OUTPUT_SIZE, OUTPUT_SIZE), (0, 0, 0, 0))
    quadrants = (
        ((left, top, source_x, source_y), (0, 0), (target_x, target_y)),
        ((source_x, top, right, source_y), (target_x, 0), (OUTPUT_SIZE - target_x, target_y)),
        ((left, source_y, source_x, bottom), (0, target_y), (target_x, OUTPUT_SIZE - target_y)),
        (
            (source_x, source_y, right, bottom),
            (target_x, target_y),
            (OUTPUT_SIZE - target_x, OUTPUT_SIZE - target_y),
        ),
    )
    for source_box, target_origin, target_size in quadrants:
        output.alpha_composite(resize_quadrant(source, source_box, target_size), target_origin)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / source_path.with_suffix(".webp").name
    output.save(output_path, "WEBP", lossless=True, quality=100, method=4)
    return output_path


def main() -> None:
    for filename, junction in SOURCE_JUNCTIONS.items():
        output_path = normalize(SOURCE_DIR / filename, junction)
        print(output_path.relative_to(SOURCE_DIR.parent))


if __name__ == "__main__":
    main()
