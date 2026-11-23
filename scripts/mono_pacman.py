"""Recolour the Pac-Man contribution SVGs to the profile's monochrome palette.
python scripts/mono_pacman.py dist/*.svg   (the light file is overwritten with the dark one, so both match)"""
import re, sys

MAP = {
    "#0d1117": "#0a0a0a", "#161b22": "#1a1a19",                       # page / empty cell
    "#0e4429": "#3a3936", "#006d32": "#6b6964", "#26a641": "#a8a59e", "#39d353": "#e8e6e1",  # levels
    "#ffffff": "#e8e6e1", "#8b949e": "#8a8780",                       # walls / labels
}
STYLE = "<style>image{filter:grayscale(1) brightness(1.4)}text{font-family:monospace}</style>"

paths = sys.argv[1:]
dark = next(p for p in paths if "dark" in p)
s = open(dark, encoding="utf8").read()
for a, b in MAP.items():
    s = re.sub(a, b, s, flags=re.I)
s = s.replace('fill="yellow"', 'fill="#e8e6e1"')
s = re.sub(r'values="([^"]*)"', lambda m: 'values="%s"' % ";".join(
    {"yellow": "#e8e6e1", "red": "#8a8780"}.get(v, v) for v in m.group(1).split(";")), s)
s = s.replace("<defs>", STYLE + "<defs>", 1)
for p in paths:
    open(p, "w", encoding="utf8").write(s)
print("recoloured", paths)
