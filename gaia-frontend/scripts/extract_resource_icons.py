#!/usr/bin/env python3
"""Extract real ore and QIC artwork from high-resolution board assets.

No generative reconstruction is used. The ore comes from the artifact scan;
its printed quantity is replaced with adjacent face texture. The QIC comes
directly from the standard-tech scan. Both backgrounds are removed with
geometry masks before a final Lanczos resize.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


FRONTEND_DIR = Path(__file__).resolve().parents[1]
ICON_DIR = FRONTEND_DIR / "src/assets/icons"
ORE_SOURCE = (
    FRONTEND_DIR
    / "src/assets/icons/source/ore_artifact_reference.jpg"
)
QIC_SOURCE = (
    FRONTEND_DIR
    / "src/assets/icons/source/qic_standard_tech_reference.jpg"
)

ORE_CROP = (195, 160, 320, 276)
ORE_POLYGON = ((12, 4), (113, 5), (121, 85), (120, 112), (3, 112), (1, 86))
ORE_DIGIT_BOX = (45, 15, 84, 80)
ORE_CLEAN_TEXTURE_BOX = (15, 15, 44, 80)
ORE_SCALE = 8

QIC_CROP = (535, 375, 760, 615)
QIC_POLYGONS = (
    ((53, 39), (173, 39), (222, 119), (175, 211), (56, 211), (2, 119)),
)
QIC_SCALE = 4
MASK_SCALE = 4


def antialiased_mask(
    size: tuple[int, int],
    polygons: tuple[tuple[tuple[int, int], ...], ...],
) -> Image.Image:
    large = Image.new("L", (size[0] * MASK_SCALE, size[1] * MASK_SCALE), 0)
    draw = ImageDraw.Draw(large)
    for polygon in polygons:
        draw.polygon(
            [(x * MASK_SCALE, y * MASK_SCALE) for x, y in polygon],
            fill=255,
        )
    return large.resize(size, Image.Resampling.LANCZOS)


def remove_ore_quantity(ore: Image.Image) -> Image.Image:
    rgba = ore.convert("RGBA")
    replacement = rgba.copy()
    mask = Image.new("L", rgba.size, 0)
    left, top, right, bottom = ORE_DIGIT_BOX
    clean_texture = rgba.crop(ORE_CLEAN_TEXTURE_BOX).resize(
        (right - left, bottom - top),
        Image.Resampling.LANCZOS,
    )
    replacement.alpha_composite(clean_texture, (left, top))
    ImageDraw.Draw(mask).rounded_rectangle(
        (left, top, right, bottom),
        radius=4,
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(1.4))
    return Image.composite(replacement, rgba, mask)


def extract_ore() -> Image.Image:
    with Image.open(ORE_SOURCE) as opened:
        ore = opened.convert("RGBA").crop(ORE_CROP)
    ore = remove_ore_quantity(ore)
    ore.putalpha(antialiased_mask(ore.size, (ORE_POLYGON,)))
    return ore.resize(
        (ore.width * ORE_SCALE, ore.height * ORE_SCALE),
        Image.Resampling.LANCZOS,
    ).filter(ImageFilter.UnsharpMask(radius=1.2, percent=90, threshold=3))


def extract_qic() -> Image.Image:
    with Image.open(QIC_SOURCE) as opened:
        qic = opened.convert("RGBA").crop(QIC_CROP)
    qic.putalpha(antialiased_mask(qic.size, QIC_POLYGONS))
    qic = qic.resize(
        (qic.width * QIC_SCALE, qic.height * QIC_SCALE),
        Image.Resampling.LANCZOS,
    ).filter(ImageFilter.UnsharpMask(radius=1.0, percent=70, threshold=3))
    # The TTS texture stores this printed face 90 degrees clockwise.
    return qic.transpose(Image.Transpose.ROTATE_90)


def main() -> None:
    outputs = {
        ICON_DIR / "ore.png": extract_ore(),
        ICON_DIR / "qic.png": extract_qic(),
    }
    for path, image in outputs.items():
        image.save(path, "PNG", optimize=True)
        print(f"{path.relative_to(FRONTEND_DIR)} {image.size}")


if __name__ == "__main__":
    main()
