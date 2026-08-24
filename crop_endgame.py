from PIL import Image
import os

img = Image.open(os.path.expanduser("~/projects/gaia/assets/images/endGameBonus.png"))
out = os.path.expanduser("~/projects/gaia/assets/images/endgame")
os.makedirs(out, exist_ok=True)

w = 199
h = 128

# x=0: 빈칸
crop = img.crop((0, 0, w, h))
crop.save(f"{out}/endgame_empty.png")

for i in range(1, 7):
    x = i * w
    crop = img.crop((x, 0, x + w, h))
    crop.save(f"{out}/endgame{i}.png")

print(f"✅ 완료: {len(os.listdir(out))}개")
