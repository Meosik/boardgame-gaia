"""Build correctly oriented, separately cropped Federation-token faces.

The 1254 px source images contain the gray and green faces side by side.  The
green face is printed upside down in those source sheets, so the UI-ready asset
is the right-hand face rotated by 180 degrees.  Token ids follow the engine's
reward ids rather than the source filenames.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ASSET_DIR = Path(__file__).resolve().parents[1] / "src" / "assets" / "federation_tokens"
OUTPUT_DIR = ASSET_DIR / "normalized"
BACK_OUTPUT_DIR = OUTPUT_DIR / "back"
SOURCE_SIZE = (1254, 1254)
RIGHT_FACE_LEFT = 620
RIGHT_FACE_LEFT_BY_SOURCE = {"06.png": 630}
LEFT_FACE_RIGHT = 634
ALPHA_NOISE_CUTOFF = 96

# Source 01 is the Gleens-only token.  Sources 04 and 05 are ordered by their
# scan filenames, not by the engine reward ids, hence the intentional swap.
SOURCE_BY_TOKEN_ID = {
    1: "02.png",  # 12 VP
    2: "03.png",  # 8 VP + 1 QIC
    3: "05.png",  # 8 VP + 2 power
    4: "04.png",  # 7 VP + 2 ore
    5: "06.png",  # 7 VP + 6 credits
    6: "07.png",  # 6 VP + 2 knowledge
    16: "01.png",  # Gleens: 1 ore + 1 knowledge + 2 credits
}


def normalize_token(source: Path) -> Image.Image:
    image = Image.open(source).convert("RGBA")
    if image.size != SOURCE_SIZE:
        raise ValueError(f"{source.name}: expected {SOURCE_SIZE}, got {image.size}")

    face_left = RIGHT_FACE_LEFT_BY_SOURCE.get(source.name, RIGHT_FACE_LEFT)
    face = image.crop((face_left, 0, SOURCE_SIZE[0], SOURCE_SIZE[1]))
    face = face.transpose(Image.Transpose.ROTATE_180)

    alpha = face.getchannel("A")
    alpha = alpha.point(lambda value: 0 if value <= ALPHA_NOISE_CUTOFF else value)
    face.putalpha(alpha)

    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError(f"{source.name}: no visible token pixels")
    return face.crop(bounds)


def normalize_back_token(source: Path) -> Image.Image:
    """Extract the upright gray face without upscaling or redrawing it."""

    image = Image.open(source).convert("RGBA")
    if image.size != SOURCE_SIZE:
        raise ValueError(f"{source.name}: expected {SOURCE_SIZE}, got {image.size}")

    face = image.crop((0, 0, LEFT_FACE_RIGHT, SOURCE_SIZE[1]))
    alpha = face.getchannel("A")
    alpha = alpha.point(lambda value: 0 if value <= ALPHA_NOISE_CUTOFF else value)

    # The two photographed faces nearly touch. A few sources leave a thin,
    # disconnected strip from the green face at the far-right crop edge.
    # Keep the widest continuous occupied x-range (the gray token itself)
    # rather than baking that neighboring strip into the normalized asset.
    x_projection, _ = alpha.getprojection()
    occupied_runs: list[tuple[int, int]] = []
    run_start: int | None = None
    for x, occupied in enumerate((*x_projection, 0)):
        if occupied and run_start is None:
            run_start = x
        elif not occupied and run_start is not None:
            occupied_runs.append((run_start, x))
            run_start = None
    if not occupied_runs:
        raise ValueError(f"{source.name}: no visible back-face pixels")
    left, right = max(occupied_runs, key=lambda run: run[1] - run[0])
    face = face.crop((left, 0, right, face.height))
    alpha = alpha.crop((left, 0, right, alpha.height))
    face.putalpha(alpha)

    bounds = alpha.getbbox()
    if bounds is None:
        raise ValueError(f"{source.name}: no visible back-face pixels")
    return face.crop(bounds)


def restore_credit_six(face: Image.Image) -> Image.Image:
    """Restore the 6 glyph that the upscaler interpreted before sheet rotation.

    Source 06's green face is upside down on the paired source sheet. The
    upscaler redrew its inverted 6 as a visually upright 6, so rotating the
    whole face correctly turns that single glyph into a 9. Rotating the round
    credit icon once more restores the intended 6 without changing the tile.
    """

    icon_bounds = (318, 349, 528, 559)
    icon = face.crop(icon_bounds).transpose(Image.Transpose.ROTATE_180)
    mask = Image.new("L", icon.size, 0)
    ImageDraw.Draw(mask).ellipse((5, 5, icon.width - 5, icon.height - 5), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(4))

    corrected = face.copy()
    corrected.paste(icon, icon_bounds[:2], mask)
    return corrected


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BACK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for token_id, filename in SOURCE_BY_TOKEN_ID.items():
        source = ASSET_DIR / filename
        normalized = normalize_token(source)
        normalized_back = normalize_back_token(source)
        if token_id == 5:
            normalized = restore_credit_six(normalized)
        output = OUTPUT_DIR / f"fed_{token_id:02}.webp"
        back_output = BACK_OUTPUT_DIR / f"fed_{token_id:02}.webp"
        normalized.save(output, "WEBP", lossless=True, method=6)
        normalized_back.save(back_output, "WEBP", lossless=True, method=6)
        print(
            f"{filename} -> {output.relative_to(ASSET_DIR)} {normalized.size} + "
            f"{back_output.relative_to(ASSET_DIR)} {normalized_back.size}"
        )


if __name__ == "__main__":
    main()
