#!/usr/bin/env python3
"""Normalize transparent Interspace tiles to one exact flat-top hex footprint.

This stage is deliberately geometry-only. It removes transparent padding,
corrects the differing source canvases, and writes lossless RGBA assets.
Color, contrast, saturation, denoising, and sharpening belong to a later stage.

Geometry contract
-----------------
Source files: 1.png through 7.png (transparent RGBA, dimensions may differ)
Source tile crop: alpha bounding box after removing alpha values <= 96
Output canvas: 1254x1254 RGBA
Output tile bounds: left=0, top=84, right=1254, bottom=1170 (1254x1086)
Output center: (627, 627)
Output vertices: (0,627), (314,84), (940,84), (1254,627),
                 (940,1170), (314,1170)
"""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


ASSET_DIR = Path(__file__).resolve().parents[1] / "src/assets/interspace_tiles"
OUTPUT_DIR = ASSET_DIR / "normalized"

OUTPUT_SIZE = 1254
HEX_HEIGHT = 1086
HEX_TOP = (OUTPUT_SIZE - HEX_HEIGHT) // 2
HEX_BOTTOM = HEX_TOP + HEX_HEIGHT
HEX_CENTER = OUTPUT_SIZE // 2
HEX_LEFT_SHOULDER = 314
HEX_RIGHT_SHOULDER = OUTPUT_SIZE - HEX_LEFT_SHOULDER
MASK_SCALE = 4
ALPHA_NOISE_CUTOFF = 96


def hex_mask() -> Image.Image:
    scale = MASK_SCALE
    mask_size = OUTPUT_SIZE * scale
    mask = Image.new("L", (mask_size, mask_size), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(
        [
            (0, HEX_CENTER * scale),
            (HEX_LEFT_SHOULDER * scale, HEX_TOP * scale),
            (HEX_RIGHT_SHOULDER * scale, HEX_TOP * scale),
            (mask_size - 1, HEX_CENTER * scale),
            (HEX_RIGHT_SHOULDER * scale, HEX_BOTTOM * scale - 1),
            (HEX_LEFT_SHOULDER * scale, HEX_BOTTOM * scale - 1),
        ],
        fill=255,
    )
    return mask.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.Resampling.LANCZOS)


def normalize(source_path: Path, mask: Image.Image) -> Path:
    source = Image.open(source_path).convert("RGBA")
    alpha = source.getchannel("A").point(
        lambda value: 0 if value <= ALPHA_NOISE_CUTOFF else value
    )
    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError(f"{source_path.name}: no visible tile pixels")
    source.putalpha(alpha)

    tile = source.crop(bounds).resize(
        (OUTPUT_SIZE, HEX_HEIGHT), Image.Resampling.LANCZOS
    )
    output = Image.new("RGBA", (OUTPUT_SIZE, OUTPUT_SIZE), (0, 0, 0, 0))
    output.alpha_composite(tile, (0, HEX_TOP))
    output.putalpha(ImageChops.multiply(output.getchannel("A"), mask))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    number = f"{int(source_path.stem):02}"
    output_path = OUTPUT_DIR / f"{number}.webp"
    output.save(output_path, "WEBP", lossless=True, quality=100, method=4)
    return output_path


def main() -> None:
    mask = hex_mask()
    sources = sorted(ASSET_DIR.glob("[1-7].png"), key=lambda path: int(path.stem))
    if len(sources) != 7:
        raise ValueError(f"expected 7 source tiles, found {len(sources)}")

    for source_path in sources:
        output_path = normalize(source_path, mask)
        print(output_path.relative_to(ASSET_DIR.parent))


if __name__ == "__main__":
    main()
