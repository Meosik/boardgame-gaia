from PIL import Image
import colorsys, os

SRC_DIR = os.path.expanduser("~/projects/gaia/assets/images/structures")
OUT_DIR = os.path.expanduser("~/projects/gaia/assets/images/structures")

STRUCTURE_TYPES = ["mine", "researchlab", "academy", "planetary_institute", "gaiaformer", "marker", "structure6"]

# (hue, sat_override, val_boost)
COLORS = {
    "cyan":   (0.522, None,  1.0),
    "yellow": (0.134, 0.90,  1.2),
    "orange": (0.077, 0.92,  1.2),
    "pink":   (0.958, None,  1.3),
    "red":    (0.997, 0.80,  0.9),
    "gray":   (0.541, 0.10,  0.7),
    "brown":  (0.050, None,  0.7),
    "white":  (0.531, 0.05,  1.1),
}

def recolor(img_path, out_path, target_hue, sat_override=None, val_boost=1.0):
    img = Image.open(img_path).convert("RGB")
    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = [v/255 for v in pixels[x, y]]
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            if s > 0.15 and v > 0.05:
                h = target_hue
                if sat_override is not None:
                    s = sat_override
                v = min(1.0, v * val_boost)
                r, g, b = colorsys.hsv_to_rgb(h, s, v)
                pixels[x, y] = (int(r*255), int(g*255), int(b*255))
    img.save(out_path)

for color, (hue, sat, boost) in COLORS.items():
    for stype in STRUCTURE_TYPES:
        src = f"{SRC_DIR}/blue_{stype}.png"
        if not os.path.exists(src):
            print(f"  skip: blue_{stype}.png 없음")
            continue
        out = f"{OUT_DIR}/{color}_{stype}.png"
        recolor(src, out, hue, sat, boost)
        print(f"  ✅ {color}_{stype}.png")

print("완료")
