from PIL import Image
import os

img = Image.open(os.path.expanduser("~/projects/gaia/assets/images/roundBonus.png"))
out = os.path.expanduser("~/projects/gaia/assets/images/roundbonus")
os.makedirs(out, exist_ok=True)

w = 182
h = img.size[1]

# x=0: 타일 뒷면
crop = img.crop((0, 0, w, h))
crop.save(f"{out}/roundbonus_back.png")

# x=182~: roundBonus1~11
for i in range(1, 12):
    x = i * w
    crop = img.crop((x, 0, x + w, h))
    crop.save(f"{out}/roundbonus{i}.png")

print(f"✅ 완료: {len(os.listdir(out))}개")
