from PIL import Image
import os

img = Image.open(os.path.expanduser("~/projects/gaia/assets/images/techs.png"))
out = os.path.expanduser("~/projects/gaia/assets/images/techs")
os.makedirs(out, exist_ok=True)

w = 150
h = 116

# x=0: 빈칸
crop = img.crop((0, 0, w, h))
crop.save(f"{out}/tech_empty.png")

for i in range(1, 25):
    x = i * w
    crop = img.crop((x, 0, x + w, h))
    crop.save(f"{out}/tech{i}.png")

print(f"✅ 완료: {len(os.listdir(out))}개")
