"""Typographic portrait: the photo is redrawn with a repeating phrase, each letter shaded by the photo.
python scripts/portrait.py <photo> <out.png> [size]"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

PHRASE = "I SEE IT I BUILD IT I SHIP IT  SHAHAB  GOMMAGE  RAPID PROTOTYPER  PRODUCT DEVELOPER  "
src, out = sys.argv[1], sys.argv[2]
SIZE = int(sys.argv[3]) if len(sys.argv) > 3 else 1200
CW, CH = 6, 9                      # character cell in px
FONT = ImageFont.truetype("consolab.ttf", 10)

img = Image.open(src).convert("RGB")
cols, rows = SIZE // CW, SIZE // CH
small = img.resize((cols, rows), Image.LANCZOS)
lum = ImageEnhance.Contrast(small.convert("L")).enhance(1.35).load()
rgb = small.load()

canvas = Image.new("L", (SIZE, SIZE), 10)
d = ImageDraw.Draw(canvas)
k = 0
for y in range(rows):
    for x in range(cols):
        r, g, b = rgb[x, y]
        v = lum[x, y]
        if b > r + 8:                # teal/navy background -> faint
            v = v * .15
        ch = PHRASE[k % len(PHRASE)]
        k += 1
        if ch == " ":
            continue
        d.text((x * CW, y * CH - 1), ch, font=FONT, fill=int(min(255, 14 + v ** 1.15 * .95)))
canvas = canvas.filter(ImageFilter.UnsharpMask(1, 60))
# monochrome "paper on ink" palette to match the profile
pal = Image.merge("RGB", [canvas.point(lambda p: int(10 + p * (232 - 10) / 255)),
                          canvas.point(lambda p: int(10 + p * (230 - 10) / 255)),
                          canvas.point(lambda p: int(10 + p * (225 - 10) / 255))])
pal.save(out, optimize=True)
print(out, pal.size)
