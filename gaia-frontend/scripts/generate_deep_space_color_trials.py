#!/usr/bin/env python3
"""Generate front-side Deep Space shadow-colour trials at one fixed scale."""

from pathlib import Path

from PIL import Image, ImageDraw

from normalize_expansion_space_tiles import (
    DEEP_DIR,
    DEEP_OUTPUT_SIZE,
    DEEP_SOURCE_INDEX_BY_SECTOR,
    DEEP_SOURCE_SIZE,
    FRONTEND_DIR,
    deep_space_mask,
    normalize_image,
)


OUTPUT_DIR = DEEP_DIR / "color_trials"
CONTACT_SHEET = OUTPUT_DIR / "front-color-comparison.png"
STANDARD_DIR = FRONTEND_DIR / "src/assets/space_sectors"

# The standard-sector dark-background median is approximately RGB(1, 3, 30),
# while the original Deep Space scans are approximately RGB(27, 27, 33).
# Apply that difference only to shadows; planets and bright printed details
# remain unchanged.
SHADOW_RGB_DELTA = (-25, -24, -2)
SHADOW_FULL_BELOW = 60
SHADOW_NONE_ABOVE = 150
MATCH_STRENGTH_BY_SECTOR = {
    11: 0.00,
    12: 0.15,
    13: 0.30,
    14: 0.45,
    15: 0.60,
    16: 0.75,
    17: 0.90,
    18: 1.00,
}


def shift_channel(channel: Image.Image, delta: int) -> Image.Image:
    return channel.point(lambda value: max(0, min(255, value + delta)))


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
    matched = Image.composite(shifted, rgba.convert("RGB"), shadow_mask(rgba, strength))
    output = matched.convert("RGBA")
    output.putalpha(alpha)
    return output


def draw_tile(
    sheet: Image.Image,
    draw: ImageDraw.ImageDraw,
    image: Image.Image,
    x: int,
    y: int,
    thumb_size: tuple[int, int],
    label: str,
) -> None:
    tile = image.convert("RGBA")
    tile.thumbnail(thumb_size, Image.Resampling.LANCZOS)
    sheet.paste(tile, (x, y), tile)
    draw.text((x + 6, y + thumb_size[1] + 8), label, fill=(230, 235, 240))


def build_contact_sheet(paths: list[tuple[int, int, Path]]) -> None:
    columns = 4
    thumb_size = (330, 328)
    gap = 22
    label_height = 42
    rows = 3
    sheet = Image.new(
        "RGB",
        (
            gap + columns * (thumb_size[0] + gap),
            gap + rows * (thumb_size[1] + label_height + gap),
        ),
        (15, 15, 19),
    )
    draw = ImageDraw.Draw(sheet)

    for column, sector_id in enumerate((1, 3, 5, 9)):
        reference = Image.open(STANDARD_DIR / f"{sector_id:02d}.png")
        x = gap + column * (thumb_size[0] + gap)
        draw_tile(
            sheet,
            draw,
            reference,
            x,
            gap,
            thumb_size,
            f"Standard sector {sector_id:02d} reference",
        )

    for index, (sector_id, percent, path) in enumerate(paths):
        image = Image.open(path)
        x = gap + (index % columns) * (thumb_size[0] + gap)
        y = gap + (1 + index // columns) * (thumb_size[1] + label_height + gap)
        draw_tile(
            sheet,
            draw,
            image,
            x,
            y,
            thumb_size,
            f"Deep {sector_id} front · colour match {percent}%",
        )
    sheet.save(CONTACT_SHEET, "PNG", compress_level=6)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_mask = deep_space_mask(DEEP_SOURCE_SIZE)
    output_mask = deep_space_mask(DEEP_OUTPUT_SIZE)
    generated: list[tuple[int, int, Path]] = []
    for sector_id, strength in MATCH_STRENGTH_BY_SECTOR.items():
        source_index = DEEP_SOURCE_INDEX_BY_SECTOR[sector_id]
        source_path = DEEP_DIR / f"deep_space_sector_{source_index:02d}.jpg"
        output, _, _ = normalize_image(
            source_path,
            DEEP_SOURCE_SIZE,
            DEEP_OUTPUT_SIZE,
            source_mask,
            output_mask,
        )
        matched = match_standard_shadows(output, strength)
        percent = round(strength * 100)
        output_path = OUTPUT_DIR / f"{sector_id}-front-color-{percent}.png"
        matched.save(output_path, "PNG", compress_level=6)
        generated.append((sector_id, percent, output_path))
        print(output_path.relative_to(FRONTEND_DIR))
    build_contact_sheet(generated)
    print(CONTACT_SHEET.relative_to(FRONTEND_DIR))


if __name__ == "__main__":
    main()
