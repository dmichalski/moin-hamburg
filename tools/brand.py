#!/usr/bin/env python3
"""Draw the integration's icon from the renderer's own shapes and colours.

    brand.py             write custom_components/moin_hamburg/brand/icon.png and icon@2x.png
    brand.py --svg FILE  only the drawing, as SVG

Home Assistant shows brand images from the integration's `brand` folder
(icon.png 256 x 256, icon@2x.png 512 x 512; logo and dark variants fall back
to the icon). The icon is the dusk scene of the skyline -- Elbphilharmonie,
Michel with the evening sun behind it, TV tower, a crane -- on a rounded tile,
so it carries its own background on light and dark pages alike; a faint
inner edge keeps the dark water apart from dark pages. Needs Google
Chrome (headless) for the pictures and Pillow to scale them down.
"""
import argparse
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PKG = ROOT / 'custom_components' / 'moin_hamburg'
BRAND = PKG / 'brand'
sys.dont_write_bytecode = True
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(ROOT / 'tools'))

from render.city import crane, speicherstadt  # noqa: E402
from render.palette import PALETTES  # noqa: E402
from showcase import _chrome  # noqa: E402

S = 512                    # drawing size
RADIUS = 112               # corner radius of the tile
K = 1.75                   # skyline scale: x 56..300 of the skyline fills the tile
TX, TY = 42 - 56 * K, 350 - 190 * K
WATER = 350                # waterline in the tile
SUN = (212, 142, 62)       # the renderer's evening sun, a little higher, in skyline coordinates


def _stops(stops):
    return ''.join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)


def svg(size=S):
    p = PALETTES['dusk-clear']
    sx, sy = TX + SUN[0] * K, TY + SUN[1] * K
    far = ('M0 190 V150 H12 V138 H26 V146 H40 V132 H52 V142 H180 V128 H196 V136 H244 L250 22 L256 136 H262 V120 '
           'H276 V134 H300 V126 H318 V112 L324 100 L330 112 V140 H346 V130 H362 V142 H376 V134 H390 V190 Z')
    near = ' '.join([
        speicherstadt(0, 66),
        'M70 190 V128 H176 V190 Z',                                         # Kaispeicher
        'M196 190 V150 H250 V190 Z M212 150 V92 H230 V150 Z M209 92 V86 H233 V92 Z M214 86 V70 H228 V86 Z '
        'M215 70 Q221 57 227 70 Z M218 60 H224 V48 H218 Z M219 48 L221 26 L223 48 Z',   # Michel
        'M280 190 V40 H284 V190 Z M274 60 H290 V67 H274 Z M276 71 H288 V74 H276 Z M281.4 40 V8 H282.6 V40 Z',
        'M292 172 H400 V190 H292 Z M0 184 H400 V190 H0 Z',                  # containers, quay wall
        crane(300),
    ])
    glass = ('M70 128 V96 Q80 80 92 92 Q104 70 120 88 Q132 72 146 88 Q158 78 168 94 Q172 90 176 96 V128 Z')
    lights = ''.join(f'<rect x="{x}" y="{y}" width="3" height="2"/>' for x, y in
                     [(78, 106), (90, 114), (104, 100), (116, 114), (128, 98), (140, 108), (152, 116), (162, 106),
                      (96, 122), (134, 122), (84, 118), (148, 96), (200, 160), (238, 164)])
    town = (f'<path fill="{p["far"]}" d="{far}"/><path fill="{p["near"]}" d="{near}"/>'
            f'<path stroke="{p["near"]}" stroke-width="0.8" fill="none" d="M322 112 L290 134 M322 112 L354 134"/>'
            f'<path fill="{p["glass"]}" d="{glass}"/>'
            f'<path stroke="{p["near"]}" stroke-width="0.6" opacity="0.45" fill="none" d="M70 104 H176 M70 112 H176 M70 120 H176"/>'
            f'<g fill="{p["win"]}" opacity="{p["win_op"]}">{lights}</g>'
            f'<circle cx="221" cy="101" r="3.2" fill="{p["glass"]}"/>'
            f'<g fill="#ff5a4f"><circle cx="282" cy="8" r="1.6"/><circle cx="250" cy="24" r="1.6"/>'
            f'<circle cx="322" cy="112" r="1.6"/></g>')
    sc, _ = p['shimmer']
    # The sun's path on the water: bars that narrow and fade towards the viewer's edge of the tile.
    bars = ''.join(f'<rect x="{sx - w / 2:.1f}" y="{y}" width="{w:.1f}" height="5" rx="2.5" fill="{sc}" opacity="{o:.2f}"/>'
                   for y, w, o in [(362, 120, .75), (378, 92, .6), (394, 104, .5), (410, 70, .45), (426, 82, .35),
                                   (442, 50, .3), (458, 60, .25), (474, 34, .2)])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {S} {S}">
<defs>
<clipPath id="tile"><rect width="{S}" height="{S}" rx="{RADIUS}"/></clipPath>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">{_stops(p['sky'])}</linearGradient>
<linearGradient id="water" x1="0" y1="0" x2="0" y2="1">{_stops(p['water'])}</linearGradient>
<radialGradient id="sun"><stop offset="0" stop-color="#ffe4ae"/><stop offset=".5" stop-color="#ffb062"/><stop offset="1" stop-color="#ef7a4b"/></radialGradient>
<radialGradient id="glow"><stop offset="0" stop-color="#ff9650" stop-opacity=".55"/><stop offset="1" stop-color="#ff9650" stop-opacity="0"/></radialGradient>
<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".45"/><stop offset=".6" stop-color="#fff" stop-opacity="0"/></linearGradient>
<mask id="refl"><rect y="{WATER}" width="{S}" height="{S - WATER}" fill="url(#fade)"/></mask>
<g id="town" transform="translate({TX:.2f} {TY:.2f}) scale({K})">{town}</g>
</defs>
<g clip-path="url(#tile)">
<rect width="{S}" height="{WATER}" fill="url(#sky)"/>
<g fill="#fff"><circle cx="70" cy="62" r="2.2" opacity=".8"/><circle cx="128" cy="34" r="1.6" opacity=".6"/><circle cx="196" cy="78" r="1.4" opacity=".5"/></g>
<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{150 * K:.0f}" fill="url(#glow)"/>
<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{SUN[2] * K:.0f}" fill="url(#sun)"/>
<use href="#town"/>
<rect y="{WATER}" width="{S}" height="{S - WATER}" fill="url(#water)"/>
<g mask="url(#refl)"><use href="#town" transform="translate(0 {2 * WATER}) scale(1 -1)"/></g>
{bars}
<rect width="{S}" height="{S}" rx="{RADIUS}" fill="none" stroke="#fff" stroke-opacity=".1" stroke-width="6"/>
</g>
</svg>
'''


def write_pngs(out=BRAND):
    from PIL import Image
    chrome = _chrome()
    extra = ['--no-sandbox'] if os.environ.get('CI') else []
    big = 1024                 # drawn at twice the largest size, then scaled down
    with tempfile.TemporaryDirectory() as tmp:
        src, png = pathlib.Path(tmp, 'icon.svg'), pathlib.Path(tmp, 'icon.png')
        src.write_text(svg(big), encoding='utf-8')
        subprocess.run([chrome, '--headless', '--disable-gpu', '--hide-scrollbars', *extra,
                        '--default-background-color=00000000', f'--window-size={big},{big}',
                        f'--screenshot={png}', src.as_uri()], check=True, capture_output=True, timeout=120)
        with Image.open(png) as im:
            im = im.convert('RGBA')
            if im.size != (big, big):
                raise SystemExit(f'Chrome drew {im.size}, expected {big} x {big}')
            out.mkdir(exist_ok=True)
            for name, size in (('icon.png', 256), ('icon@2x.png', 512)):
                path = out / name
                im.resize((size, size), Image.Resampling.LANCZOS).save(path, optimize=True)
                print(f'{path.relative_to(ROOT)}: {size} x {size}, {path.stat().st_size // 1024} KB')


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--svg', type=pathlib.Path, help='write only the drawing to this file')
    a = ap.parse_args(argv)
    if a.svg:
        a.svg.write_text(svg(), encoding='utf-8')
    else:
        write_pngs()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
