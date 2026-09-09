#!/usr/bin/env python3
"""Normalize reviewed structure renders and derive every player color.

Only the blue source sprites have reliable transparency.  The reviewed blue
upscales therefore define geometry and detail; the existing low-resolution
sprites provide color-only lookup tables for the other eight colors.  This
keeps every color on an identical silhouette without asking an image model to
redraw the same building nine different ways.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


SCALE = 4
ALPHA_THRESHOLD = 128
COLORS = (
    "blue",
    "brown",
    "cyan",
    "gray",
    "orange",
    "pink",
    "red",
    "white",
    "yellow",
)
ASSETS = {
    "mine": ("mine", ("mine.png", "blue_mine.png")),
    # The legacy BGA crops were named after sprite indices, not the physical
    # pieces: `researchlab` is the Trading Station and `structure6` is the
    # Research Lab.  Outputs use semantic names so they cannot be swapped again.
    "trading_station": (
        "researchlab",
        ("trading_station.png", "blue_trading_station.png", "blue_researchlab.png"),
    ),
    "research_lab": (
        "structure6",
        ("research_lab.png", "blue_research_lab.png", "blue_structure6.png"),
    ),
    "planetary_institute": (
        "planetary_institute",
        ("planetary_institute.png", "blue_planetary_institute.png"),
    ),
    "academy": ("academy", ("academy.png", "blue_academy.png")),
    "marker": ("marker", ("satellite.png", "marker.png", "blue_marker.png")),
    "gaiaformer": (
        "gaiaformer",
        ("gaiaformer.png", "gaia_former.png", "blue_gaiaformer.png"),
    ),
}


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path.home() / "다운로드/gaia_upscaled_assets/structures/blue",
        help="Directory containing the reviewed blue structure renders.",
    )
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=project_root / "src/assets/structures",
        help="Directory containing the current per-color reference sprites.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "src/assets/structures/upscaled",
        help="Directory for normalized 4x RGBA PNG sprites.",
    )
    return parser.parse_args()


def find_source(source_dir: Path, aliases: tuple[str, ...]) -> Path:
    for alias in aliases:
        candidate = source_dir / alias
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"none of {aliases} exists in {source_dir}")


def opaque_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    if alpha.getextrema()[0] != 0:
        raise ValueError("generated building must have a transparent background")
    bbox = alpha.point(lambda value: 255 if value >= ALPHA_THRESHOLD else 0).getbbox()
    if bbox is None:
        raise ValueError("generated building has no opaque pixels")
    return bbox


def scaled_bbox(bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    return tuple(value * SCALE for value in bbox)  # type: ignore[return-value]


def clear_transparent_rgb(image: Image.Image) -> None:
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha == 0:
                pixels[x, y] = (0, 0, 0, 0)


def normalize_blue(generated_path: Path, reference_path: Path) -> Image.Image:
    generated = Image.open(generated_path).convert("RGBA")
    reference = Image.open(reference_path).convert("RGBA")
    target_size = (reference.width * SCALE, reference.height * SCALE)
    target_bbox = scaled_bbox(opaque_bbox(reference))
    target_width = target_bbox[2] - target_bbox[0]
    target_height = target_bbox[3] - target_bbox[1]

    artwork = generated.crop(opaque_bbox(generated)).resize(
        (target_width, target_height), Image.Resampling.LANCZOS
    )
    normalized = Image.new("RGBA", target_size, (0, 0, 0, 0))
    normalized.alpha_composite(artwork, dest=(target_bbox[0], target_bbox[1]))
    normalized.putalpha(
        reference.getchannel("A").resize(target_size, Image.Resampling.LANCZOS)
    )
    clear_transparent_rgb(normalized)
    return normalized


def luminance(red: int, green: int, blue: int) -> int:
    return (299 * red + 587 * green + 114 * blue) // 1000


def color_luts(blue_reference: Image.Image, color_reference: Image.Image) -> tuple[list[int], list[int], list[int]]:
    blue = blue_reference.convert("RGBA")
    target = color_reference.convert("RGB")
    sums = [[0] * 256 for _ in range(3)]
    counts = [0] * 256

    for (red, green, blue_value, alpha), target_pixel in zip(blue.getdata(), target.getdata()):
        if alpha < ALPHA_THRESHOLD:
            continue
        level = luminance(red, green, blue_value)
        counts[level] += 1
        for channel in range(3):
            sums[channel][level] += target_pixel[channel]

    prefix_counts = [0]
    prefix_sums = [[0] for _ in range(3)]
    for level in range(256):
        prefix_counts.append(prefix_counts[-1] + counts[level])
        for channel in range(3):
            prefix_sums[channel].append(prefix_sums[channel][-1] + sums[channel][level])

    luts = [[0] * 256 for _ in range(3)]
    for level in range(256):
        radius = 2
        sample_count = 0
        low = high = level
        while sample_count < 8 and radius <= 255:
            low = max(0, level - radius)
            high = min(255, level + radius)
            sample_count = prefix_counts[high + 1] - prefix_counts[low]
            radius *= 2
        if sample_count == 0:
            continue
        for channel in range(3):
            total = prefix_sums[channel][high + 1] - prefix_sums[channel][low]
            luts[channel][level] = round(total / sample_count)

    return luts[0], luts[1], luts[2]


def recolor(
    normalized_blue: Image.Image,
    blue_reference: Image.Image,
    color_reference: Image.Image,
) -> Image.Image:
    red_lut, green_lut, blue_lut = color_luts(blue_reference, color_reference)
    gray = ImageOps.grayscale(normalized_blue)
    result = Image.merge(
        "RGBA",
        (
            gray.point(red_lut),
            gray.point(green_lut),
            gray.point(blue_lut),
            normalized_blue.getchannel("A"),
        ),
    )
    clear_transparent_rgb(result)
    return result


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for asset_name, (reference_name, aliases) in ASSETS.items():
        generated_path = find_source(args.source_dir, aliases)
        blue_reference_path = args.reference_dir / f"blue_{reference_name}.png"
        blue_reference = Image.open(blue_reference_path).convert("RGBA")
        normalized_blue = normalize_blue(generated_path, blue_reference_path)

        for color in COLORS:
            output = args.output_dir / f"{color}_{asset_name}.png"
            if color == "blue":
                image = normalized_blue
            else:
                color_reference = Image.open(
                    args.reference_dir / f"{color}_{reference_name}.png"
                )
                image = recolor(normalized_blue, blue_reference, color_reference)
            image.save(output, format="PNG", optimize=True)
            print(f"{output.name}: {image.width}x{image.height} RGBA")


if __name__ == "__main__":
    main()
