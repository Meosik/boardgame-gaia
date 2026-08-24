from PIL import Image
import os

img = Image.open(os.path.expanduser("~/projects/gaia/assets/images/federationTokens.png"))
out = os.path.expanduser("~/projects/gaia/assets/images/federation")
os.makedirs(out, exist_ok=True)

w, h = 96, 119

# x=0: 빈칸
crop = img.crop((0, 0, w, h))
crop.save(f"{out}/federation_empty.png")

for i in range(1, 8):
    x = i * w
    crop = img.crop((x, 0, x + w, h))
    crop.save(f"{out}/federation{i}.png")
    crop = img.crop((x, h, x + w, h * 2))
    crop.save(f"{out}/federation{i}_used.png")

print(f"✅ 완료: {len(os.listdir(out))}개")
