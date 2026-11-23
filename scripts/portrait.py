"""Typographic portrait: the photo is redrawn with a repeating phrase, each letter shaded by the photo.
python scripts/portrait.py <photo> <out-basename> [size]   ->  <out>.png  <out>.svg  <out>.pdf
SVG/PDF are true vectors: letters are font outlines (no font needed to open them)."""
import sys, zlib
from PIL import Image, ImageDraw, ImageOps
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.basePen import BasePen

PHRASE = "I SEE IT I BUILD IT I SHIP IT  SHAHAB  GOMMAGE  RAPID PROTOTYPER  PRODUCT DEVELOPER  "
FONT_FILE = r"C:\Windows\Fonts\consolab.ttf"
CW, CH, FS = 6, 9, 11          # cell width/height and font size, px
LEVELS = 8                     # gray steps (also the number of fill colours in the vectors)
INK, PAPER = (10, 10, 10), (232, 230, 225)


def cells(src, size):
    img = Image.open(src).convert("RGB")
    cols, rows = size // CW, size // CH
    small = img.resize((cols, rows), Image.LANCZOS)
    lum = ImageOps.autocontrast(small.convert("L"), cutoff=1).load()
    rgb = small.load()
    out, k = [], 0
    for y in range(rows):
        for x in range(cols):
            ch = PHRASE[k % len(PHRASE)]
            k += 1
            r, g, b = rgb[x, y]
            if ch == " " or b > r + 8:          # spaces and the teal/navy background stay black
                continue
            v = min(1., max(0., (lum[x, y] / 255 - .2) / .5)) ** .9   # hard S-curve: crush darks, push skin to white
            if v < .06:
                continue
            out.append((x * CW, y * CH, ch, min(LEVELS - 1, int(v * LEVELS))))
    return out


def tone(level):
    t = .22 + .78 * level / (LEVELS - 1)
    return tuple(round(INK[i] + (PAPER[i] - INK[i]) * t) for i in range(3))


def glyphs(chars):
    f = TTFont(FONT_FILE)
    gs, cmap = f.getGlyphSet(), f.getBestCmap()
    return f, gs, {c: cmap[ord(c)] for c in chars}


def write_svg(cs, size, path):
    f, gs, names = glyphs({c for _, _, c, _ in cs})
    s = FS / f["head"].unitsPerEm
    defs = []
    for c, n in names.items():
        pen = SVGPathPen(gs)
        gs[n].draw(pen)
        defs.append(f'<path id="g{ord(c)}" transform="scale({s:.5f} {-s:.5f})" d="{pen.getCommands()}"/>')
    groups = []
    for lv in range(LEVELS):
        uses = "".join(f'<use href="#g{ord(c)}" x="{x}" y="{y + CH - 2}"/>' for x, y, c, l in cs if l == lv)
        groups.append(f'<g fill="#{"%02x%02x%02x" % tone(lv)}">{uses}</g>')
    open(path, "w", encoding="utf8").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<defs>{"".join(defs)}</defs><rect width="{size}" height="{size}" fill="#0a0a0a"/>{"".join(groups)}</svg>')


class PdfPen(BasePen):
    def __init__(self, gs):
        super().__init__(gs)
        self.ops = []

    def _moveTo(self, p): self.ops.append(f"{p[0]} {p[1]} m")
    def _lineTo(self, p): self.ops.append(f"{p[0]} {p[1]} l")
    def _curveToOne(self, a, b, c): self.ops.append(f"{a[0]} {a[1]} {b[0]} {b[1]} {c[0]} {c[1]} c")
    def _closePath(self): self.ops.append("h")


def write_pdf(cs, size, path):
    f, gs, names = glyphs({c for _, _, c, _ in cs})
    s = FS / f["head"].unitsPerEm
    objs, xobj = [], {}
    for c, n in names.items():                      # one Form XObject per glyph, in font units
        pen = PdfPen(gs)
        gs[n].draw(pen)
        body = " ".join(pen.ops) + " f"
        objs.append(f"<< /Type /XObject /Subtype /Form /BBox [-200 -400 1400 1400] /Length {len(body)} >>\nstream\n{body}\nendstream")
        xobj[c] = len(objs)                         # placeholder index, fixed below
    ops = [f"{INK[0]/255:.3f} {INK[1]/255:.3f} {INK[2]/255:.3f} rg 0 0 {size} {size} re f"]
    for lv in range(LEVELS):
        r, g, b = tone(lv)
        ops.append(f"{r/255:.3f} {g/255:.3f} {b/255:.3f} rg")
        for x, y, c, l in cs:
            if l == lv:
                ops.append(f"q {s:.5f} 0 0 {s:.5f} {x} {size - (y + CH - 2)} cm /G{ord(c)} Do Q")
    content = zlib.compress("\n".join(ops).encode())
    # object numbers: 1 catalog, 2 pages, 3 page, 4 content, 5.. glyph forms
    base = 5
    res = " ".join(f"/G{ord(c)} {base + i} 0 R" for i, c in enumerate(names))
    head = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {size} {size}] /Contents 4 0 R /Resources << /XObject << {res} >> >> >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []

    def add(b):
        offsets.append(len(out))
        out.extend(f"{len(offsets)} 0 obj\n".encode() + b + b"\nendobj\n")

    for h in head:
        add(h.encode())
    add(f"<< /Length {len(content)} /Filter /FlateDecode >>\nstream\n".encode() + content + b"\nendstream")
    for o in objs:
        add(o.encode())
    xref = len(out)
    out.extend(f"xref\n0 {len(offsets)+1}\n0000000000 65535 f \n".encode())
    out.extend("".join(f"{o:010d} 00000 n \n" for o in offsets).encode())
    out.extend(f"trailer\n<< /Size {len(offsets)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    open(path, "wb").write(out)


def write_png(cs, size, path):
    from PIL import ImageFont
    font = ImageFont.truetype(FONT_FILE, FS)
    im = Image.new("RGB", (size, size), INK)
    d = ImageDraw.Draw(im)
    for x, y, c, l in cs:
        d.text((x, y + CH - 2), c, font=font, fill=tone(l), anchor="ls")
    im.save(path, optimize=True)


if __name__ == "__main__":
    src, base = sys.argv[1], sys.argv[2]
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 1200
    cs = cells(src, size)
    write_png(cs, size, base + ".png")
    write_svg(cs, size, base + ".svg")
    write_pdf(cs, size, base + ".pdf")
    print(len(cs), "letters ->", base + ".png/.svg/.pdf")
