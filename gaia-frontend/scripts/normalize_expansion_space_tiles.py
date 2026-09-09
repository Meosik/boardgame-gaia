#!/usr/bin/env python3
"""Rebuild Deep Space and Interspace art from the original scans.

This is a deterministic, non-generative pipeline. It uses one 2x Lanczos
resize, shared physical masks, protected shadow matching, star reduction, and
geometry-derived border repair for each asset family.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import math
import shutil
import statistics
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


FRONTEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = FRONTEND_DIR.parent
DEEP_DIR = FRONTEND_DIR / "src/assets/deep_space_sectors"
INTERSPACE_DIR = FRONTEND_DIR / "src/assets/interspace_tiles"
DEEP_WEBP_DIR = DEEP_DIR / "normalized"
INTERSPACE_WEBP_DIR = INTERSPACE_DIR / "normalized"
BACKUP_ROOT = PROJECT_DIR / ".omh/backups/expansion_space_tiles"

DEEP_SOURCE_SIZE = (822, 818)
DEEP_OUTPUT_SIZE = tuple(value * 2 for value in DEEP_SOURCE_SIZE)
INTERSPACE_SOURCE_SIZE = (466, 466)
INTERSPACE_OUTPUT_SIZE = tuple(value * 2 for value in INTERSPACE_SOURCE_SIZE)
MASK_SCALE = 4
DEEP_SHADOW_MATCH_STRENGTH = 0.85
INTERSPACE_SHADOW_MATCH_STRENGTH = 0.40
SHADOW_RGB_DELTA = (-25, -24, -2)
SHADOW_FULL_BELOW = 60
SHADOW_NONE_ABOVE = 150
KUWAHARA_RADIUS = 2
STAR_LUMA_THRESHOLD = 170
STAR_SATURATION_LIMIT = 110
STAR_COMPONENT_AREA = (4, 80)
STAR_COMPONENT_SPAN_LIMIT = 16
STAR_SURROUND_LUMA_LIMIT = 85
STAR_SURROUND_SATURATION_LIMIT = 145
OUTLINE_COLOR = (242, 247, 250, 245)
DEEP_OUTLINE_WIDTH = 7
INTERSPACE_OUTLINE_WIDTH = 6

# The scan filenames follow the TTS model order, not the printed sector ids.
# Each front image is side A; the matching `_back` image is side B.
DEEP_SOURCE_INDEX_BY_SECTOR = {
    11: 3,
    12: 4,
    13: 5,
    14: 6,
    15: 7,
    16: 8,
    17: 1,
    18: 2,
}

# Measured once from the shared 466x466 TTS texture template. All seven
# Interspace scans use this exact central flat-top hex footprint.
INTERSPACE_SOURCE_VERTICES = (
    (0, 233),
    (116, 27),
    (350, 27),
    (465, 233),
    (350, 438),
    (116, 438),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize expansion space tiles from their original scans."
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backing up the currently rendered expansion tile assets.",
    )
    parser.add_argument(
        "--outline-only",
        action="store_true",
        help="Redraw white borders on current PNG/WebP outputs without rebuilding art.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def antialiased_polygon_mask(
    size: tuple[int, int], vertices: list[tuple[float, float]]
) -> Image.Image:
    width, height = size
    large = Image.new("L", (width * MASK_SCALE, height * MASK_SCALE), 0)
    ImageDraw.Draw(large).polygon(
        [(round(x * MASK_SCALE), round(y * MASK_SCALE)) for x, y in vertices],
        fill=255,
    )
    return large.resize(size, Image.Resampling.LANCZOS)


def deep_space_polygons(
    size: tuple[int, int],
) -> tuple[tuple[tuple[float, float], ...], ...]:
    width, height = size
    radius = width / 3.5
    hex_height = math.sqrt(3) * radius
    top = (height - 2 * hex_height) / 2
    center_y = height / 2
    junction_x = radius * 2

    centers = (
        (radius, center_y),
        (junction_x + radius / 2, top + hex_height / 2),
        (junction_x + radius / 2, top + hex_height * 1.5),
    )
    polygons: list[tuple[tuple[float, float], ...]] = []
    for center_x, center_y_value in centers:
        polygons.append((
            (center_x + radius, center_y_value),
            (center_x + radius / 2, center_y_value + hex_height / 2),
            (center_x - radius / 2, center_y_value + hex_height / 2),
            (center_x - radius, center_y_value),
            (center_x - radius / 2, center_y_value - hex_height / 2),
            (center_x + radius / 2, center_y_value - hex_height / 2),
        ))
    return tuple(polygons)


def deep_space_mask(size: tuple[int, int]) -> Image.Image:
    """Return the exact union of the three printed flat-top hexes."""
    width, height = size
    large = Image.new("L", (width * MASK_SCALE, height * MASK_SCALE), 0)
    draw = ImageDraw.Draw(large)
    for vertices in deep_space_polygons(size):
        draw.polygon(
            [
                (round(x * MASK_SCALE), round(y * MASK_SCALE))
                for x, y in vertices
            ],
            fill=255,
        )
    return large.resize(size, Image.Resampling.LANCZOS)


def interspace_polygon(size: tuple[int, int]) -> tuple[tuple[float, float], ...]:
    scale_x = size[0] / INTERSPACE_SOURCE_SIZE[0]
    scale_y = size[1] / INTERSPACE_SOURCE_SIZE[1]
    return tuple(
        (x * scale_x, y * scale_y) for x, y in INTERSPACE_SOURCE_VERTICES
    )


def interspace_mask(size: tuple[int, int]) -> Image.Image:
    return antialiased_polygon_mask(size, list(interspace_polygon(size)))


def apply_mask(image: Image.Image, mask: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    rgba.putalpha(ImageChops.multiply(rgba.getchannel("A"), mask))
    return rgba


def repair_outline(
    image: Image.Image,
    polygons: tuple[tuple[tuple[float, float], ...], ...],
    stroke_width: int,
) -> Image.Image:
    """Redraw faded scan borders without changing the tile alpha footprint."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for vertices in polygons:
        points = [(round(x), round(y)) for x, y in vertices]
        draw.line(
            points + [points[0]],
            fill=OUTLINE_COLOR,
            width=stroke_width,
            joint="curve",
        )
    output = Image.alpha_composite(rgba, overlay)
    output.putalpha(alpha)
    return output


def reduce_star_count(image: Image.Image) -> Image.Image:
    """Remove a deterministic half of small white stars, preserving artwork."""
    rgba = image.convert("RGBA")
    rgb = rgba.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    hsv_pixels = rgb.convert("HSV").load()
    candidates = bytearray(width * height)

    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            if (
                luma >= STAR_LUMA_THRESHOLD
                and hsv_pixels[x, y][1] <= STAR_SATURATION_LIMIT
            ):
                candidates[y * width + x] = 1

    seen = bytearray(width * height)
    components: list[tuple[list[tuple[int, int]], tuple[int, int, int, int]]] = []
    for index, candidate in enumerate(candidates):
        if not candidate or seen[index]:
            continue
        stack = [index]
        seen[index] = 1
        points: list[tuple[int, int]] = []
        while stack:
            current = stack.pop()
            current_y, current_x = divmod(current, width)
            points.append((current_x, current_y))
            for neighbor_x, neighbor_y in (
                (current_x - 1, current_y),
                (current_x + 1, current_y),
                (current_x, current_y - 1),
                (current_x, current_y + 1),
            ):
                if not (0 <= neighbor_x < width and 0 <= neighbor_y < height):
                    continue
                neighbor = neighbor_y * width + neighbor_x
                if candidates[neighbor] and not seen[neighbor]:
                    seen[neighbor] = 1
                    stack.append(neighbor)

        if not (STAR_COMPONENT_AREA[0] <= len(points) <= STAR_COMPONENT_AREA[1]):
            continue
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        bounds = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
        if (
            bounds[2] - bounds[0] <= STAR_COMPONENT_SPAN_LIMIT
            and bounds[3] - bounds[1] <= STAR_COMPONENT_SPAN_LIMIT
        ):
            components.append((points, bounds))

    replacement = rgb.copy()
    replacement_pixels = replacement.load()
    replacement_mask = Image.new("L", rgb.size, 0)
    replacement_mask_pixels = replacement_mask.load()
    for points, (left, top, right, bottom) in components:
        surrounding_luma: list[float] = []
        surrounding_saturation: list[int] = []
        surrounding_colors: list[tuple[int, int, int]] = []
        for y in range(max(0, top - 6), min(height, bottom + 6)):
            for x in range(max(0, left - 6), min(width, right + 6)):
                if left - 2 <= x < right + 2 and top - 2 <= y < bottom + 2:
                    continue
                red, green, blue = pixels[x, y]
                luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
                surrounding_luma.append(luma)
                surrounding_saturation.append(hsv_pixels[x, y][1])
                if luma < 100:
                    surrounding_colors.append((red, green, blue))
        if (
            not surrounding_colors
            or statistics.median(surrounding_luma) >= STAR_SURROUND_LUMA_LIMIT
            or statistics.median(surrounding_saturation)
            >= STAR_SURROUND_SATURATION_LIMIT
        ):
            continue

        center_x = sum(point[0] for point in points) // len(points)
        center_y = sum(point[1] for point in points) // len(points)
        if ((center_x * 73856093) ^ (center_y * 19349663)) & 1:
            continue
        background = tuple(
            int(statistics.median([color[channel] for color in surrounding_colors]))
            for channel in range(3)
        )
        for point_x, point_y in points:
            for y in range(max(0, point_y - 2), min(height, point_y + 3)):
                for x in range(max(0, point_x - 2), min(width, point_x + 3)):
                    replacement_pixels[x, y] = background
                    replacement_mask_pixels[x, y] = 255

    replacement_mask = replacement_mask.filter(ImageFilter.GaussianBlur(0.7))
    output = Image.composite(replacement, rgb, replacement_mask).convert("RGBA")
    output.putalpha(rgba.getchannel("A"))
    return output


def shadow_mask(image: Image.Image, strength: float) -> Image.Image:
    luma = image.convert("RGB").convert("L")

    def mask_value(value: int) -> int:
        if value <= SHADOW_FULL_BELOW:
            weight = 1.0
        elif value >= SHADOW_NONE_ABOVE:
            weight = 0.0
        else:
            weight = (SHADOW_NONE_ABOVE - value) / (
                SHADOW_NONE_ABOVE - SHADOW_FULL_BELOW
            )
        return round(255 * strength * weight)

    return luma.point(mask_value)


def shift_channel(channel: Image.Image, delta: int) -> Image.Image:
    return channel.point(lambda value: max(0, min(255, value + delta)))


def match_standard_shadows(image: Image.Image, strength: float) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    red, green, blue = rgba.convert("RGB").split()
    shifted = Image.merge(
        "RGB",
        (
            shift_channel(red, SHADOW_RGB_DELTA[0]),
            shift_channel(green, SHADOW_RGB_DELTA[1]),
            shift_channel(blue, SHADOW_RGB_DELTA[2]),
        ),
    )
    matched = Image.composite(
        shifted,
        rgba.convert("RGB"),
        shadow_mask(rgba, strength),
    ).convert("RGBA")
    matched.putalpha(alpha)
    return matched


def kuwahara_smooth(image: Image.Image) -> Image.Image:
    source = io.BytesIO()
    image.convert("RGB").save(source, "PNG")
    result = subprocess.run(
        ["convert", "png:-", "-kuwahara", str(KUWAHARA_RADIUS), "png:-"],
        input=source.getvalue(),
        capture_output=True,
        check=True,
    )
    with Image.open(io.BytesIO(result.stdout)) as smoothed:
        return smoothed.convert("RGB")


def reduce_paper_texture(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    rgb = rgba.convert("RGB")
    alpha = rgba.getchannel("A")
    luma = rgb.convert("L")
    background = shadow_mask(rgba, 1.0)
    edges = luma.filter(ImageFilter.FIND_EDGES).point(
        lambda value: min(255, value * 2)
    )
    protected_background = ImageChops.subtract(
        ImageChops.multiply(background, alpha), edges
    )
    output = Image.composite(
        kuwahara_smooth(rgb), rgb, protected_background
    ).convert("RGBA")
    output.putalpha(alpha)
    return output


def alpha_weighted_luma(image: Image.Image) -> float:
    weighted_luma = 0.0
    total_alpha = 0
    for red, green, blue, alpha in image.convert("RGBA").getdata():
        if alpha == 0:
            continue
        luma = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        weighted_luma += luma * alpha
        total_alpha += alpha
    if total_alpha == 0:
        raise ValueError("image has no visible pixels")
    return weighted_luma / total_alpha


def next_backup_dir() -> Path:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUP_ROOT / f"before-original-2x-{timestamp}"
    suffix = 1
    while backup_dir.exists():
        backup_dir = BACKUP_ROOT / f"before-original-2x-{timestamp}-{suffix}"
        suffix += 1
    return backup_dir


def backup_outputs() -> Path | None:
    file_groups = {
        "deep-png": [
            DEEP_DIR / f"{sector_id}-{side}.png"
            for sector_id in DEEP_SOURCE_INDEX_BY_SECTOR
            for side in (1, 2)
        ],
        "interspace-png": [
            INTERSPACE_DIR / f"{tile_id}.png" for tile_id in range(1, 8)
        ],
    }
    directory_groups = {
        "deep-normalized": DEEP_WEBP_DIR,
        "interspace-normalized": INTERSPACE_WEBP_DIR,
    }
    existing_files = {
        name: [path for path in paths if path.exists()]
        for name, paths in file_groups.items()
    }
    existing_files = {name: paths for name, paths in existing_files.items() if paths}
    existing_dirs = {
        name: path for name, path in directory_groups.items() if path.exists()
    }
    if not existing_files and not existing_dirs:
        return None

    backup_dir = next_backup_dir()
    backup_dir.mkdir(parents=True)
    for name, paths in existing_files.items():
        destination_dir = backup_dir / name
        destination_dir.mkdir()
        for path in paths:
            shutil.copy2(path, destination_dir / path.name)
    for name, source_dir in existing_dirs.items():
        shutil.copytree(source_dir, backup_dir / name)
    return backup_dir


def normalize_image(
    source_path: Path,
    source_size: tuple[int, int],
    output_size: tuple[int, int],
    source_mask: Image.Image,
    output_mask: Image.Image,
    reduce_stars: bool = False,
) -> tuple[Image.Image, float, float]:
    with Image.open(source_path) as opened:
        opened.load()
        if opened.size != source_size:
            raise ValueError(
                f"{source_path.name}: expected {source_size}, found {opened.size}"
            )
        prepared = reduce_star_count(opened) if reduce_stars else opened.convert("RGBA")
        source = apply_mask(prepared, source_mask)
        source_luma = alpha_weighted_luma(source)
        output = apply_mask(
            prepared.resize(output_size, Image.Resampling.LANCZOS),
            output_mask,
        )
        output_luma = alpha_weighted_luma(output)
    return output, source_luma, output_luma


def save_outputs(
    source_path: Path,
    png_path: Path,
    webp_path: Path,
    source_size: tuple[int, int],
    output_size: tuple[int, int],
    source_mask: Image.Image,
    output_mask: Image.Image,
    shadow_match_strength: float | None = None,
    reduce_texture: bool = False,
    reduce_stars: bool = False,
    outline_polygons: tuple[tuple[tuple[float, float], ...], ...] | None = None,
    outline_width: int = 0,
) -> None:
    output, source_luma, output_luma = normalize_image(
        source_path,
        source_size,
        output_size,
        source_mask,
        output_mask,
        reduce_stars=reduce_stars,
    )
    if shadow_match_strength is not None:
        output = match_standard_shadows(output, shadow_match_strength)
    if reduce_texture:
        output = reduce_paper_texture(output)
    if outline_polygons is not None:
        output = repair_outline(output, outline_polygons, outline_width)
    if shadow_match_strength is not None or reduce_texture:
        output_luma = alpha_weighted_luma(output)
    output.save(png_path, "PNG", compress_level=6)
    output.save(webp_path, "WEBP", lossless=True, quality=100, method=4)

    print(
        f"{source_path.name} {source_size[0]}x{source_size[1]}"
        f" -> {png_path.relative_to(FRONTEND_DIR)} +"
        f" {webp_path.relative_to(FRONTEND_DIR)}"
        f" | {output_size[0]}x{output_size[1]}"
        f" | luma {source_luma:.4f} -> {output_luma:.4f}"
        f" ({output_luma - source_luma:+.4f})"
        f" | sha256 {sha256(png_path)[:12]}"
    )


def normalize_deep_space() -> None:
    DEEP_WEBP_DIR.mkdir(parents=True, exist_ok=True)
    source_mask = deep_space_mask(DEEP_SOURCE_SIZE)
    output_mask = deep_space_mask(DEEP_OUTPUT_SIZE)
    for sector_id, source_index in DEEP_SOURCE_INDEX_BY_SECTOR.items():
        for side_number, suffix in ((1, ""), (2, "_back")):
            source_path = DEEP_DIR / f"deep_space_sector_{source_index:02d}{suffix}.jpg"
            png_path = DEEP_DIR / f"{sector_id}-{side_number}.png"
            webp_path = DEEP_WEBP_DIR / f"{sector_id}-{side_number}.webp"
            save_outputs(
                source_path,
                png_path,
                webp_path,
                DEEP_SOURCE_SIZE,
                DEEP_OUTPUT_SIZE,
                source_mask,
                output_mask,
                shadow_match_strength=DEEP_SHADOW_MATCH_STRENGTH,
                reduce_texture=True,
                reduce_stars=True,
                outline_polygons=deep_space_polygons(DEEP_OUTPUT_SIZE),
                outline_width=DEEP_OUTLINE_WIDTH,
            )


def normalize_interspace() -> None:
    INTERSPACE_WEBP_DIR.mkdir(parents=True, exist_ok=True)
    source_mask = interspace_mask(INTERSPACE_SOURCE_SIZE)
    output_mask = interspace_mask(INTERSPACE_OUTPUT_SIZE)
    for tile_id in range(1, 8):
        source_path = INTERSPACE_DIR / f"interspace_{tile_id:02d}.jpg"
        png_path = INTERSPACE_DIR / f"{tile_id}.png"
        webp_path = INTERSPACE_WEBP_DIR / f"{tile_id:02d}.webp"
        save_outputs(
            source_path,
            png_path,
            webp_path,
            INTERSPACE_SOURCE_SIZE,
            INTERSPACE_OUTPUT_SIZE,
            source_mask,
            output_mask,
            shadow_match_strength=INTERSPACE_SHADOW_MATCH_STRENGTH,
            reduce_stars=True,
            outline_polygons=(interspace_polygon(INTERSPACE_OUTPUT_SIZE),),
            outline_width=INTERSPACE_OUTLINE_WIDTH,
        )


def repair_current_outlines() -> None:
    """Update only borders so approved colour and star treatment stay untouched."""
    for sector_id in DEEP_SOURCE_INDEX_BY_SECTOR:
        for side_number in (1, 2):
            png_path = DEEP_DIR / f"{sector_id}-{side_number}.png"
            webp_path = DEEP_WEBP_DIR / f"{sector_id}-{side_number}.webp"
            with Image.open(png_path) as opened:
                output = repair_outline(
                    opened.convert("RGBA"),
                    deep_space_polygons(opened.size),
                    DEEP_OUTLINE_WIDTH,
                )
            output.save(png_path, "PNG", compress_level=6)
            output.save(webp_path, "WEBP", lossless=True, quality=100, method=4)
            print(f"outline: {png_path.relative_to(FRONTEND_DIR)}")

    for tile_id in range(1, 8):
        png_path = INTERSPACE_DIR / f"{tile_id}.png"
        webp_path = INTERSPACE_WEBP_DIR / f"{tile_id:02d}.webp"
        with Image.open(png_path) as opened:
            output = repair_outline(
                opened.convert("RGBA"),
                (interspace_polygon(opened.size),),
                INTERSPACE_OUTLINE_WIDTH,
            )
        output.save(png_path, "PNG", compress_level=6)
        output.save(webp_path, "WEBP", lossless=True, quality=100, method=4)
        print(f"outline: {png_path.relative_to(FRONTEND_DIR)}")


def main() -> None:
    args = parse_args()
    if not args.no_backup:
        backup_dir = backup_outputs()
        if backup_dir is not None:
            print(f"backup: {backup_dir.relative_to(PROJECT_DIR)}")
    if args.outline_only:
        repair_current_outlines()
    else:
        normalize_deep_space()
        normalize_interspace()


if __name__ == "__main__":
    main()
