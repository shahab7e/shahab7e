"""Generates the profile SVGs (monochrome / dither / NFO style).  Run from repo root:  python scripts/gen.py"""
import base64, io, math, os, random
from html import escape
from PIL import Image, ImageDraw, ImageFilter

OUT = "assets"
INK, PAPER, GRAY, DIM = "#0a0a0a", "#e8e6e1", "#8a8780", "#3a3936"
MONO = "'JetBrains Mono','Cascadia Mono',Consolas,Menlo,'DejaVu Sans Mono',monospace"
FA = "Vazirmatn,Tahoma,'Segoe UI','Geeza Pro',sans-serif"
RM = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
W = 1200

# ------------------------------------------------------------------ pixel font 5x7
GLYPHS = {
    "A": ".###.|#...#|#...#|#####|#...#|#...#|#...#", "B": "####.|#...#|#...#|####.|#...#|#...#|####.",
    "C": ".###.|#...#|#....|#....|#....|#...#|.###.", "D": "####.|#...#|#...#|#...#|#...#|#...#|####.",
    "E": "#####|#....|#....|####.|#....|#....|#####", "F": "#####|#....|#....|####.|#....|#....|#....", "G": ".###.|#...#|#....|#.###|#...#|#...#|.###.",
    "H": "#...#|#...#|#...#|#####|#...#|#...#|#...#", "I": "#####|..#..|..#..|..#..|..#..|..#..|#####",
    "K": "#...#|#..#.|#.#..|##...|#.#..|#..#.|#...#", "L": "#....|#....|#....|#....|#....|#....|#####",
    "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#", "N": "#...#|##..#|#.#.#|#..##|#...#|#...#|#...#",
    "O": ".###.|#...#|#...#|#...#|#...#|#...#|.###.", "P": "####.|#...#|#...#|####.|#....|#....|#....",
    "R": "####.|#...#|#...#|####.|#.#..|#..#.|#...#", "S": ".####|#....|#....|.###.|....#|....#|####.",
    "T": "#####|..#..|..#..|..#..|..#..|..#..|..#..", "V": "#...#|#...#|#...#|#...#|#...#|.#.#.|..#..",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#", "X": "#...#|#...#|.#.#.|..#..|.#.#.|#...#|#...#",
    "Y": "#...#|#...#|.#.#.|..#..|..#..|..#..|..#..", "U": "#...#|#...#|#...#|#...#|#...#|#...#|.###.",
    "/": "....#|....#|...#.|..#..|.#...|#....|#....", " ": ".....|.....|.....|.....|.....|.....|.....",
}


def pixel_text(text, cx, top, cell, shadow=True):
    """Pixel-font text centred on cx. Solid paper blocks + a halftone drop shadow."""
    cols = len(text) * 6 - 1
    x0 = cx - cols * cell / 2
    solid, shade = [], []
    for i, ch in enumerate(text):
        for r, row in enumerate(GLYPHS[ch].split("|")):
            for c, on in enumerate(row):
                if on == "#":
                    x, y = x0 + (i * 6 + c) * cell, top + r * cell
                    solid.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell-1.5:.1f}" height="{cell-1.5:.1f}"/>')
                    shade.append(f'<rect x="{x+cell*.45:.1f}" y="{y+cell*.45:.1f}" width="{cell:.1f}" height="{cell:.1f}"/>')
    sh = f'<g fill="url(#ht)">{"".join(shade)}</g>' if shadow else ""
    return f'{sh}<g class="fl" fill="{PAPER}">{"".join(solid)}</g>', cols * cell


HT = (f'<pattern id="ht" width="6" height="6" patternUnits="userSpaceOnUse">'
      f'<rect width="2.4" height="2.4" fill="{GRAY}"/><rect x="3" y="3" width="2.4" height="2.4" fill="{GRAY}"/></pattern>')
FLICKER = ".fl{animation:fl 7s steps(1) infinite} @keyframes fl{0%,93%,96%,100%{opacity:1}94%{opacity:.35}95%{opacity:.8}}"


# ------------------------------------------------------------------ dither art -> 1-bit PNG data URI
def png_uri(gray, scale=2):
    """gray: PIL 'L' image. Floyd–Steinberg to 1-bit, paint ink/paper, upscale with nearest."""
    bw = gray.convert("1")
    p = Image.new("P", bw.size)
    p.putpalette([10, 10, 10, 232, 230, 225] + [0] * 762)
    p.putdata([1 if v else 0 for v in bw.get_flattened_data()])
    p = p.resize((bw.width * scale, bw.height * scale), Image.NEAREST)
    buf = io.BytesIO()
    p.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def galaxy(w=170, h=115, seed=3):
    rnd = random.Random(seed)
    img = Image.new("L", (w, h))
    px = img.load()
    cx, cy = w / 2, h / 2
    for y in range(h):
        for x in range(w):
            dx, dy = (x - cx) / (w * .42), (y - cy) / (h * .30)
            # tilt the disc
            u, v = dx * .92 + dy * .38, -dx * .38 + dy * .92
            r = math.hypot(u, v * 1.0) + 1e-6
            th = math.atan2(v, u)
            arm = (math.cos(2 * (th - 2.6 * math.log(r))) * .5 + .5) ** 3
            val = math.exp(-r * 2.1) * (.25 + .9 * arm) * 255 + math.exp(-r * r * 40) * 230
            px[x, y] = int(min(255, val + rnd.gauss(0, 10)))
    for _ in range(60):
        px[rnd.randrange(w), rnd.randrange(h)] = rnd.choice([150, 255])
    return png_uri(img)


def sphere(size=88, light=(-.6, -.5), rings=False, seed=5):
    rnd = random.Random(seed)
    img = Image.new("L", (size, size))
    px = img.load()
    R = size / 2 - 2
    lx, ly = light
    lz = math.sqrt(max(0, 1 - lx * lx - ly * ly))
    for y in range(size):
        for x in range(size):
            nx, ny = (x - size / 2) / R, (y - size / 2) / R
            d = nx * nx + ny * ny
            if d > 1:
                px[x, y] = 0
                continue
            nz = math.sqrt(1 - d)
            val = max(0, nx * lx + ny * ly + nz * lz)
            val = .08 + .92 * val ** 1.2
            if rings:  # globe graticule
                lat, lon = math.asin(ny), math.atan2(nx, nz)
                if abs((lat * 6 / math.pi) % 1 - .5) > .44 or abs((lon * 6 / math.pi) % 1 - .5) > .45:
                    val *= .35
            else:  # cratered moon
                val *= .82 + .18 * math.sin(x * .7 + rnd.random()) * math.cos(y * .6)
            px[x, y] = int(val * 255)
    return png_uri(img)


def onion(size=88):
    """Gommage onion mark (three arcs + bar), shaded, ready to dither."""
    s = 4
    big = Image.new("L", (size * s, size * s), 0)
    d = ImageDraw.Draw(big)
    c, wd = size * s / 2, int(7 * s)
    for r, tone in ((38, 150), (26, 205), (14, 255)):
        rr = r * s
        d.arc([c - rr, c - rr, c + rr, c + rr], start=0, end=315, fill=tone, width=wd)
    d.line([c, c, c + 38 * s, c], fill=255, width=wd)
    img = big.resize((size, size), Image.LANCZOS).filter(ImageFilter.GaussianBlur(.6))
    return png_uri(img)


# ------------------------------------------------------------------ building blocks
def panel(x, y, w, h, extra=""):
    return f'<rect x="{x+.75}" y="{y+.75}" width="{w-1.5}" height="{h-1.5}" rx="12" fill="none" stroke="{PAPER}" stroke-width="1.5" {extra}/>'


def label(x, y, s, size=22, fill=PAPER, anchor="start", weight=400, ls=2):
    return (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'letter-spacing="{ls}" text-anchor="{anchor}">{escape(s)}</text>')


def corners(x, y, w, h, m=14, l=22):
    p = (f"M{x+m} {y+m+l}V{y+m}H{x+m+l} M{x+w-m-l} {y+m}H{x+w-m}V{y+m+l} "
         f"M{x+m} {y+h-m-l}V{y+h-m}H{x+m+l} M{x+w-m-l} {y+h-m}H{x+w-m}V{y+h-m-l}")
    return f'<path d="{p}" fill="none" stroke="{PAPER}" stroke-width="2"/>'


def wave(x, y, w, h, n=90, seed=1):
    rnd = random.Random(seed)
    step = w / n
    bars = []
    for i in range(n):
        bh = h * (.15 + .85 * abs(math.sin(i * .23)) * rnd.random())
        bars.append(f'<rect x="{x+i*step:.1f}" y="{y+(h-bh)/2:.1f}" width="2" height="{bh:.1f}" class="wv" '
                    f'style="animation-delay:-{rnd.uniform(0, 2):.2f}s;transform-origin:{x+i*step:.1f}px {y+h/2:.1f}px"/>')
    return f'<g fill="{PAPER}">{"".join(bars)}</g>'


WAVE_CSS = ".wv{animation:wv 1.8s ease-in-out infinite alternate} @keyframes wv{from{transform:scaleY(.35)}to{transform:scaleY(1)}}"


def svg(name, h, body, css="", aria=""):
    open(os.path.join(OUT, name), "w", encoding="utf8").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{escape(aria)}">'
        f'<style>{css} {RM}</style><defs>{HT}</defs>'
        f'<rect width="{W}" height="{h}" rx="16" fill="{INK}"/>{body}</svg>')


# ------------------------------------------------------------------ hero
def hero():
    H = 404
    title, tw = pixel_text("SHAHAB", 372 + (W - 372) / 2, 100, 17)
    sweep = (f'<rect class="sc" x="1" y="62" width="358" height="10" fill="{PAPER}" opacity=".12"/>')
    stars = "".join(f'<rect class="tw" x="{random.Random(i).uniform(20, 340):.0f}" y="{random.Random(i+50).uniform(78, 290):.0f}" '
                    f'width="3" height="3" fill="{PAPER}" style="animation-delay:-{i*.37:.2f}s"/>' for i in range(9))
    body = (
        panel(0, 0, 440, 52) + label(24, 34, "SHAHAB7E.NFO") + label(416, 34, "1 / 1", fill=GRAY, anchor="end")
        + panel(452, 0, 748, 52) + label(1176, 34, "// RAPID PROTOTYPER & PRODUCT DEVELOPER", anchor="end")
        + panel(0, 62, 360, 240)
        + f'<image href="{galaxy()}" x="10" y="72" width="340" height="230" style="image-rendering:pixelated" preserveAspectRatio="xMidYMid slice"/>'
        + stars + sweep + corners(0, 62, 360, 240)
        + panel(372, 62, 828, 240) + title
        + label(372 + (W - 372) / 2, 262, "I SEE IT. I BUILD IT. I SHIP IT.", fill=GRAY, anchor="middle")
        + panel(0, 314, 1100, 90) + wave(24, 330, 1052, 58)
        + panel(1112, 314, 88, 90)
        + '<g class="sp" style="transform-origin:1156px 359px">' + ''.join(
            f'<rect x="1153" y="335" width="6" height="48" fill="{PAPER}" transform="rotate({a} 1156 359)"/>' for a in (0, 45, 90, 135)) + '</g>'
    )
    css = (FLICKER + WAVE_CSS +
           ".tw{animation:tw 2.4s steps(2) infinite} @keyframes tw{50%{opacity:0}}"
           ".sc{animation:sc 5s linear infinite} @keyframes sc{from{transform:translateY(0)}to{transform:translateY(228px)}}"
           ".sp{animation:sp 14s linear infinite} @keyframes sp{to{transform:rotate(360deg)}}")
    svg("hero.svg", H, body, css, "SHAHAB — Rapid Prototyper & Product Developer. I see it, I build it, I ship it.")


# ------------------------------------------------------------------ section header strip
def header(name, num):
    H = 92
    t, tw = pixel_text(name, 0, 22, 7, shadow=False)
    t = t.replace('class="fl" ', f'transform="translate({tw/2 + 28} 0)" ')
    body = (t + f'<line x1="{tw+56}" y1="46" x2="{W-110}" y2="46" stroke="{PAPER}" stroke-width="1.5" stroke-dasharray="2 6"/>'
            + label(W - 28, 54, f"// {num:02d}", fill=GRAY, anchor="end"))
    svg(f"h-{name.lower().replace(' ', '-').replace('/', '')}.svg", H, body, "", name)


# ------------------------------------------------------------------ Gommage feature
SPECS = [("PLATFORM", "WINDOWS · LINUX · ANDROID"), ("NETWORK", "TOR · 3 HOPS"),
         ("BRIDGES", "OBFS4 · WEBTUNNEL · SNOWFLAKE · MEEK"), ("MODES", "PROXY · WHOLE-SYSTEM VPN"),
         ("KILL SWITCH", "FAIL-CLOSED · WFP · NFTABLES"), ("TELEMETRY", "NONE. NO ACCOUNT.")]
NOTES = ["Swipe once. Gommage tests", "bridges fastest-first,", "remembers what worked and",
         "pulls fresh lists when Tor", "is blocked. Whole-system", "mode routes every app —", "Telegram, games — through Tor."]


def gommage():
    H = 662
    title, _ = pixel_text("GOMMAGE", 600, 96, 15)
    rows = ""
    for i, (k, v) in enumerate(SPECS):
        y = 358 + i * 40
        rows += label(28, y, k, fill=GRAY) + label(712, y, v, anchor="end", ls=1)
        rows += f'<line x1="28" y1="{y+16}" x2="712" y2="{y+16}" stroke="{DIM}" stroke-width="1" stroke-dasharray="2 5"/>'
    notes = "".join(label(770, 372 + i * 32, l, size=22, ls=0) for i, l in enumerate(NOTES))
    body = (
        panel(0, 0, 290, 56) + label(24, 37, "◢ FEATURED BUILD")
        + panel(302, 0, 596, 56) + label(600, 37, "GOMMAGE // ONE-TAP TOR CLIENT", anchor="middle")
        + panel(910, 0, 290, 56) + label(1176, 37, "OPEN SOURCE", anchor="end")
        # sun / title / onion
        + panel(0, 68, 200, 200) + f'<image href="{sphere(90, rings=True)}" x="10" y="78" width="180" height="180" style="image-rendering:pixelated"/>'
        + corners(0, 68, 200, 200, 10, 16)
        + panel(212, 68, 776, 200) + title
        + f'<text x="600" y="246" text-anchor="middle" direction="rtl" font-family="{FA}" font-size="24" fill="{GRAY}">اتصال به تور با یک لمس، برای عبور از فیلترینگ سنگین</text>'
        + panel(1000, 68, 200, 200) + f'<image href="{onion(90)}" x="1010" y="78" width="180" height="180" style="image-rendering:pixelated"/>'
        + corners(1000, 68, 200, 200, 10, 16)
        # specs / notes
        + panel(0, 280, 740, 300) + label(28, 318, "═ SPECS", weight=700) + rows
        + panel(752, 280, 448, 300) + label(770, 318, "═ RELEASE NOTES", weight=700) + notes
        + panel(0, 592, 1200, 70) + label(28, 635, "INSTALL", fill=GRAY)
        + label(170, 635, "Releases → Gommage-windows.zip → unzip → run Gommage.exe", ls=0)
        + f'<rect class="cur" x="1150" y="616" width="13" height="24" fill="{PAPER}"/>'
    )
    css = FLICKER + ".cur{animation:b 1s steps(1) infinite} @keyframes b{50%{opacity:0}}"
    svg("gommage.svg", H, body, css, "Gommage — one-tap Tor client for people behind heavy censorship")


# ------------------------------------------------------------------ project cards (2 per row, shown at 49%)
PROJECTS = [
    ("jam-jahan-nama", "01 / LIVE", "JAM-JAHAN-NAMA", "جام جهان‌نما", ["Iran-centred world history", "timeline: who ruled where, when."], "shahab7e.github.io/jam-jahan-nama"),
    ("asmari-care-map", "02 / LIVE", "ASMARI-CARE-MAP", "", ["Map + search of contracted", "medical centres in Tehran."], "shahab7e.github.io/asmari-care-map"),
    ("academia-platform", "03 / REPO", "ACADEMIA", "", ["Persian-first learning platform:", "courses, exams, VOD, shop."], "django · react 19"),
    ("ariverse-timeline", "04 / REPO", "ARIVERSE", "", ["Interactive timeline", "presentation."], "html · js"),
]


def project(repo, tag, name, fa, desc, foot):
    CW, CH = 600, 300
    fa_t = (f'<text x="{CW-28}" y="{100}" text-anchor="end" font-family="{FA}" font-size="28" fill="{GRAY}">{escape(fa)}</text>' if fa else "")
    body = (panel(0, 0, CW, CH) + label(28, 50, tag, fill=GRAY, size=24) + label(CW - 28, 50, "↗", anchor="end", size=26)
            + f'<line x1="0" y1="72" x2="{CW}" y2="72" stroke="{PAPER}" stroke-width="1.5"/>'
            + label(28, 140, name, size=40, weight=800, ls=1) + fa_t
            + "".join(label(28, 192 + i * 34, l, size=26, fill=GRAY, ls=0) for i, l in enumerate(desc))
            + f'<line x1="28" y1="246" x2="{CW-28}" y2="246" stroke="{DIM}" stroke-dasharray="2 5"/>'
            + label(28, 280, foot, size=22, ls=0))
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}" role="img" aria-label="{name}">'
         f'<rect width="{CW}" height="{CH}" rx="12" fill="{INK}"/>{body}</svg>')
    open(os.path.join(OUT, f"p-{repo}.svg"), "w", encoding="utf8").write(s)


# ------------------------------------------------------------------ skills (compact rows)
SKILLS = [("ux-skill", "UX", "", "senior-UX judgment: usability, a11y, forms, dark patterns"),
          ("virastari-skill", "VIRASTARI", "ویراستاری", "Persian copy-editing, every fix cites its rule"),
          ("behtar-nevisi-skill", "BEHTAR NEVISI", "بهتر بنویسیم", "rewrites Persian: correct, simple, beautiful")]


def skill(repo, name, fa, desc, i):
    H = 92
    body = (panel(0, 0, 92, H) + label(46, 58, f"0{i+1}", anchor="middle", fill=GRAY)
            + panel(104, 0, W - 104, H) + label(132, 56, name, size=26, weight=800)
            + label(132 + len(name) * 17 + 30, 56, "— " + desc, size=22, fill=GRAY, ls=0)
            + (f'<text x="{W-28}" y="58" text-anchor="end" font-family="{FA}" font-size="26" fill="{PAPER}">{escape(fa)}</text>' if fa
               else label(W - 28, 56, "CLAUDE SKILL", anchor="end", fill=GRAY, size=20)))
    svg(f"s-{repo}.svg", H, body, "", f"{name} — Claude skill")


# ------------------------------------------------------------------ terminal (monochrome)
LINES = [
    ("cmd", [("whoami", PAPER)]),
    ("out", [("shahab", PAPER), (" — rapid prototyper & product developer. I imagine it, then I build it.", GRAY)]),
    ("cmd", [("cat stack.txt", PAPER)]),
    ("out", [("TypeScript React Next.js Vite │ Django DRF Python PHP │ Claude Code", GRAY)]),
    ("cmd", [("ls ~/public", PAPER)]),
    ("out", [("gommage/  jam-jahan-nama/  asmari-care-map/  academia-platform/", PAPER)]),
    ("cmd", [('./build --next "something cool"', PAPER)]),
    ("out", [("✔ shipped.", PAPER), ("  next idea loading…", GRAY)]),
    ("cmd", []),
]


def terminal():
    X0, Y0, LH, FS = 36, 92, 31, 22
    CW = FS * .6
    H = Y0 + LH * (len(LINES) - 1) + 30
    t, ev, cur = .6, [], [(0., X0 + 2 * CW, Y0)]
    for i, (kind, segs) in enumerate(LINES):
        y, n = Y0 + i * LH, sum(len(s) for s, _ in segs)
        if kind == "cmd":
            e = [(t, 2 * CW)]
            cur.append((t, X0 + 2 * CW, y))
            t += .5
            for j in range(1, n + 1):
                t += .055
                e.append((t, (2 + j) * CW))
                cur.append((t, X0 + (2 + j) * CW, y))
            t += .35
        else:
            t += .12
            e = [(t, W)]
        ev.append(e)
    T = t + 4.5

    def anim(attr, pts, first):
        kt = [0.] + [p / T for p, _ in pts]
        for k in range(1, len(kt)):
            kt[k] = max(kt[k], kt[k - 1] + 1e-5)
        vs = [first] + [v for _, v in pts]
        return (f'<animate attributeName="{attr}" dur="{T:.2f}s" repeatCount="indefinite" calcMode="discrete" '
                f'keyTimes="{";".join(f"{k:.5f}" for k in kt)}" values="{";".join(f"{v:.1f}" for v in vs)}"/>')

    clips, body = [], []
    for i, ((kind, segs), e) in enumerate(zip(LINES, ev)):
        y = Y0 + i * LH
        clips.append(f'<clipPath id="c{i}"><rect x="{X0}" y="{y-24}" height="{LH}" width="0">{anim("width", e, 0)}</rect></clipPath>')
        pre = f'<tspan fill="{GRAY}">❯ </tspan>' if kind == "cmd" else ""
        body.append(f'<text x="{X0}" y="{y}" clip-path="url(#c{i})" xml:space="preserve">{pre}'
                    + "".join(f'<tspan fill="{c}">{escape(s)}</tspan>' for s, c in segs) + "</text>")
    cx = anim("x", [(p, x) for p, x, _ in cur[1:]], cur[0][1])
    cy = anim("y", [(p, y - 20) for p, _, y in cur[1:]], cur[0][2] - 20)
    out = (panel(0, 0, W, 50) + label(24, 33, "~/shahab — zsh") + label(W - 24, 33, "■ □ ×", anchor="end", fill=GRAY)
           + panel(0, 0, W, H) + f'<defs>{"".join(clips)}</defs>' + "".join(body)
           + f'<rect class="cur" x="{cur[0][1]:.1f}" y="{cur[0][2]-20}" width="{CW:.1f}" height="26" fill="{PAPER}">{cx}{cy}</rect>')
    svg("terminal.svg", H, out, f"text{{font:{FS}px {MONO}}} .cur{{animation:b 1s steps(1) infinite}} @keyframes b{{50%{{opacity:0}}}}",
        "Terminal: whoami — shahab, rapid prototyper & product developer")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".svg"):
            os.remove(os.path.join(OUT, f))
    hero(); gommage(); terminal()
    for i, (n, num) in enumerate([("FEATURED", 1), ("INDEX", 2), ("SKILLS", 3), ("ABOUT", 4), ("ACTIVITY", 5)]):
        header(n, num)
    for p in PROJECTS:
        project(*p)
    for i, s in enumerate(SKILLS):
        skill(*s, i)
    print("ok", sorted(os.listdir(OUT)))
