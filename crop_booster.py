from PIL import Image
import os

img = Image.open(os.path.expanduser("~/projects/gaia/assets/images/boosterTile.png"))
out = os.path.expanduser("~/projects/gaia/assets/images/boosters")
os.makedirs(out, exist_ok=True)

w = 116
h = 353  # 706 / 2

# x=0: 빈칸
crop = img.crop((0, 0, w, h))
crop.save(f"{out}/booster_empty.png")

for i in range(1, 11):
    x = i * w
    # 사용 가능 (위)
    crop = img.crop((x, 0, x + w, h))
    crop.save(f"{out}/booster{i}.png")
    # 사용됨 (아래)
    crop = img.crop((x, h, x + w, h * 2))
    crop.save(f"{out}/booster{i}_used.png")

print(f"✅ 완료: {len(os.listdir(out))}개")
