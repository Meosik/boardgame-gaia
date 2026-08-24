from PIL import Image
import os

img = Image.open(os.path.expanduser("~/projects/gaia/assets/images/structures.png"))
out = os.path.expanduser("~/projects/gaia/assets/images/structures")
os.makedirs(out, exist_ok=True)

COLORS = ["blue", "yellow", "brown", "pink", "orange", "gray", "white"]

STRUCTS = {
    "planetary_institute": {"x": 0,   "w": 218, "h": 200, "y_add": 0},
    
    "academy":             {"x": 250, "w": 186, "h": 200, "y_add": 0},
    "researchlab":         {"x": 450, "w": 102, "h": 120, "y_add": 0},
    "structure6":          {"x": 600, "w": 108, "h": 120, "y_add": 0},
    "mine":                {"x": 750, "w": 69,  "h": 80, "y_add": 0},
    "marker":              {"x": 850, "w": 62,  "h": 70, "y_add": 0},
    "gaiaformer":          {"x": 750, "w": 109, "h": 100, "y_add": 100},
}

for i, color in enumerate(COLORS):
    y_base = i * 200
    for name, s in STRUCTS.items():
        y = y_base + s["y_add"]
        crop = img.crop((s["x"], y, s["x"] + s["w"], y + s["h"]))
        crop.save(f"{out}/{color}_{name}.png")

print(f"✅ 완료: {len(os.listdir(out))}개")
