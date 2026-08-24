from PIL import Image
import os

img = Image.open(os.path.expanduser("~/projects/gaia/assets/images/icons.png"))
out = os.path.expanduser("~/projects/gaia/assets/images/icons")
os.makedirs(out, exist_ok=True)

ICONS = {
    "knowledge":  {"x": 0,   "y": 0, "w": 41, "h": 40},
    "credits":    {"x": 46,  "y": 0, "w": 40, "h": 40},
    "power":      {"x": 92,  "y": 0, "w": 39, "h": 33},
    "qic":        {"x": 138, "y": 0, "w": 33, "h": 37},
    "ore":        {"x": 184, "y": 0, "w": 40, "h": 33},
    "vp":         {"x": 230, "y": 0, "w": 46, "h": 46},
    "brainstone": {"x": 277, "y": 0, "w": 40, "h": 39},
    "cross": {"x": 322, "y": 0, "w": 79, "h": 78},
    "square":     {"x": 412, "y": 0, "w": 88, "h": 77},
}

for name, s in ICONS.items():
    crop = img.crop((s["x"], s["y"], s["x"] + s["w"], s["y"] + s["h"]))
    crop.save(f"{out}/{name}.png")
    print(f"  {name}: {s['w']}x{s['h']}")

print("✅ 완료")
