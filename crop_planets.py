from PIL import Image
import os

img = Image.open(os.path.expanduser("~/projects/gaia/assets/images/planets.png"))
out = os.path.expanduser("~/projects/gaia/assets/images/planets")
os.makedirs(out, exist_ok=True)

PLANETS = ["empty", "terra", "oxide", "volcanic", "desert", "swamp", "titanium", "ice", "gaia", "transdim", "lost"]

for i, name in enumerate(PLANETS):
    x = i * 132
    crop = img.crop((x, 0, x + 132, 132))
    crop.save(f"{out}/{name}.png")

print("✅ 완료")
