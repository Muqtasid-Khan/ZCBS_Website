"""Generate the ZCBS logo family (SVG + PNG + ICO) from one source of truth.

Run:  python tools/make_brand.py
Text is converted to vector outlines so the SVGs render identically everywhere
(no font installation needed).
"""
import os, re
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import cairosvg
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "static", "brand")
os.makedirs(OUT, exist_ok=True)

NAVY, GOLD, IVORY = "#0B1B2E", "#C9A24B", "#F6F1E7"

_fonts = {}
def font(name):
    if name not in _fonts:
        f = TTFont(os.path.join(HERE, name))
        _fonts[name] = (f, f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm)
    return _fonts[name]

def text_path(text, fontfile, size, x=0, y=0, tracking=0.0, anchor="start"):
    """Return (svg path d, width). tracking is in em units."""
    f, gs, cmap, upm = font(fontfile)
    scale = size / upm
    # measure
    adv = []
    for ch in text:
        g = cmap.get(ord(ch))
        adv.append(gs[g].width * scale + tracking * size if g else size * 0.3)
    total = sum(adv) - tracking * size
    if anchor == "middle": x -= total / 2
    elif anchor == "end": x -= total
    d, cx = [], x
    for ch, a in zip(text, adv):
        g = cmap.get(ord(ch))
        if g:
            pen = SVGPathPen(gs)
            tp = TransformPen(pen, (scale, 0, 0, -scale, cx, y))
            gs[g].draw(tp)
            d.append(pen.getCommands())
        cx += a
    return " ".join(d), total

def emblem(fg=GOLD, bg=NAVY, mono=False):
    """Emblem on a 120x130 grid: an arch (institution) enclosing a flame (knowledge,
    leadership) that rises from an open book (learning) on a pillar (character)."""
    inner = bg if not mono else "none"
    flame_cut = (f'<path d="M60 56 C65 62 68 67 68 71 C68 76 64 79 60 79 C56 79 52 76 52 71 '
                 f'C52 67 56 63 60 56Z" fill="{bg}"/>') if not mono else \
                (f'<path d="M60 56 C65 62 68 67 68 71 C68 76 64 79 60 79 C56 79 52 76 52 71 '
                 f'C52 67 56 63 60 56Z" fill="#fff" fill-rule="evenodd" opacity="0"/>')
    # for mono we use an even-odd cut-out so the emblem works on any background
    flame = ('<path fill-rule="evenodd" d="M60 24 C69 39 79 51 79 67 C79 77.5 70.5 86 60 86 C49.5 86 41 77.5 41 67 '
             'C41 51 51 39 60 24Z '
             'M60 51 C65.5 59 70 64.5 70 71 C70 76.5 65.5 81 60 81 C54.5 81 50 76.5 50 71 C50 64.5 54.5 59 60 51Z" '
             f'fill="{fg}"/>')
    return f'''
  <path d="M18 116 V60 A42 42 0 0 1 102 60 V116" fill="none" stroke="{fg}" stroke-width="4.5" stroke-linecap="square"/>
  <path d="M28 116 V60 A32 32 0 0 1 92 60 V116" fill="none" stroke="{fg}" stroke-width="1.4" opacity=".55"/>
  {flame}
  <rect x="56.5" y="88" width="7" height="16" fill="{fg}"/>
  <path d="M30 112 Q45 105 60 109 Q75 105 90 112 L90 117 Q75 110 60 114 Q45 110 30 117 Z" fill="{fg}"/>
'''

def svg(w, h, body, extra=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" {extra}>'
            f'{body}</svg>')

def write(name, content):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        fh.write(content)

def png(name_svg, name_png, width, bg=None):
    cairosvg.svg2png(url=os.path.join(OUT, name_svg), write_to=os.path.join(OUT, name_png),
                     output_width=width, background_color=bg)

def stacked(fg, ink, sub, title="ZCBS Primary Logo"):
    W, H = 760, 470
    parts = [f'<title>{title}</title>', f'<g transform="translate(320 10) scale(1.0)">{emblem(fg)}</g>']
    d1, _ = text_path("ZCBS", "corm700.woff2", 92, W/2, 232, tracking=0.12, anchor="middle")
    parts.append(f'<path d="{d1}" fill="{ink}"/>')
    parts.append(f'<rect x="{W/2-60}" y="256" width="120" height="1.6" fill="{fg}"/>')
    d2, _ = text_path("ZAKARIYAN CHARACTER BUILDING SOCIETY", "corm700.woff2", 22, W/2, 296, tracking=0.13, anchor="middle")
    parts.append(f'<path d="{d2}" fill="{ink}"/>')
    d3, _ = text_path("CASPAM  |  BZU MULTAN", "corm600.woff2", 19, W/2, 330, tracking=0.34, anchor="middle")
    parts.append(f'<path d="{d3}" fill="{sub}"/>')
    return svg(W, 350, "".join(parts))

def horizontal(fg, ink, sub, title="ZCBS Horizontal Logo"):
    W, H = 860, 130
    parts = [f'<title>{title}</title>', f'<g transform="translate(0 0)">{emblem(fg)}</g>']
    d1, w1 = text_path("ZCBS", "corm700.woff2", 64, 140, 62, tracking=0.12)
    parts.append(f'<path d="{d1}" fill="{ink}"/>')
    parts.append(f'<rect x="140" y="76" width="64" height="1.6" fill="{fg}"/>')
    d2, _ = text_path("ZAKARIYAN CHARACTER BUILDING SOCIETY", "corm700.woff2", 20, 140, 100, tracking=0.12)
    parts.append(f'<path d="{d2}" fill="{ink}"/>')
    d3, _ = text_path("CASPAM  |  BZU MULTAN", "corm600.woff2", 16, 140, 124, tracking=0.34)
    parts.append(f'<path d="{d3}" fill="{sub}"/>')
    return svg(W, 130, "".join(parts))

def compact(fg, ink):
    """Emblem + ZCBS only: navbar / small sizes."""
    parts = ['<title>ZCBS Compact Logo</title>', f'<g>{emblem(fg)}</g>']
    d1, _ = text_path("ZCBS", "corm700.woff2", 66, 136, 82, tracking=0.12)
    parts.append(f'<path d="{d1}" fill="{ink}"/>')
    return svg(400, 130, "".join(parts))

# --- Emblem alone
write("zcbs-emblem.svg", svg(120, 130, f'<title>ZCBS Emblem</title>{emblem(GOLD)}'))
write("zcbs-emblem-white.svg", svg(120, 130, f'<title>ZCBS Emblem</title>{emblem("#FFFFFF")}'))
write("zcbs-emblem-black.svg", svg(120, 130, f'<title>ZCBS Emblem</title>{emblem("#000000")}'))

# --- Primary (stacked): light-background and dark-background versions (transparent)
write("zcbs-logo-primary.svg", stacked(GOLD, NAVY, "#7A6226"))           # for light backgrounds
write("zcbs-logo-primary-light.svg", stacked(GOLD, IVORY, GOLD))          # for dark backgrounds
write("zcbs-logo-mono-black.svg", stacked("#000000", "#000000", "#000000", "ZCBS Monochrome Logo"))
write("zcbs-logo-mono-white.svg", stacked("#FFFFFF", "#FFFFFF", "#FFFFFF", "ZCBS Monochrome Logo (white)"))

# --- Horizontal & compact
write("zcbs-logo-horizontal.svg", horizontal(GOLD, NAVY, "#7A6226"))
write("zcbs-logo-horizontal-light.svg", horizontal(GOLD, IVORY, GOLD))
write("zcbs-logo-horizontal-mono-black.svg", horizontal("#000000", "#000000", "#000000"))
write("zcbs-logo-compact.svg", compact(GOLD, NAVY))
write("zcbs-logo-compact-light.svg", compact(GOLD, IVORY))

# --- Favicon: gold emblem on navy rounded square
fav_body = (f'<rect width="128" height="128" rx="26" fill="{NAVY}"/>'
            f'<g transform="translate(14 8) scale(.84)">{emblem(GOLD)}</g>')
write("favicon.svg", svg(128, 128, fav_body))

# --- PNG exports
png("zcbs-logo-primary.svg", "zcbs-logo-primary.png", 1600)                       # transparent
png("zcbs-logo-primary-light.svg", "zcbs-logo-primary-light.png", 1600)           # transparent
png("zcbs-logo-primary.svg", "zcbs-logo-primary-on-ivory.png", 1600, bg=IVORY)
png("zcbs-logo-horizontal.svg", "zcbs-logo-horizontal.png", 1600)
png("zcbs-logo-mono-black.svg", "zcbs-logo-mono-black.png", 1200)
png("zcbs-emblem.svg", "zcbs-emblem.png", 800)
png("favicon.svg", "favicon-512.png", 512)
png("favicon.svg", "apple-touch-icon.png", 180)
png("favicon.svg", "favicon-32.png", 32)
im = Image.open(os.path.join(OUT, "favicon-512.png")).convert("RGBA")
im.save(os.path.join(OUT, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
# social share card (1200x630)
card = (f'<rect width="1200" height="630" fill="{NAVY}"/>'
        f'<g transform="translate(220 120) scale(1.0)">'
        + re.sub(r'<svg[^>]*>', '<g>', stacked(GOLD, IVORY, GOLD)).replace("</svg>", "</g>") + '</g>')
write("og-card.svg", svg(1200, 630, card))
png("og-card.svg", "og-card.png", 1200)
print("brand files:", sorted(os.listdir(OUT)))
