"""The base scene: sky, sun or moon, clouds, the city, the Elbe, the ferry, rain and snow.

compose() draws the scene for one palette and takes the layers as ready-made
SVG fragments at fixed slots: behind the city, inside the city (these are
mirrored in the water), on the Elbphilharmonie glass, on the ferry and over
everything. Wind speeds up clouds, rain and snow and slants them; the moon
shows its phase. Below high tide the Elbe sinks and bares the quay wall; the
mirror image, the glitter and the ferry go down with it.
"""
import math
import random

from . import city as c
from .palette import BASE, H, OX, PALETTES, SKY_TOP, TIDE_DROP, TIDE_STEPS, W

MOON_COLOR = '#f3efd9'


def num(n):
    """Compact number: one decimal, no trailing zero."""
    s = f'{n:.1f}'
    return s[:-2] if s.endswith('.0') else s


def moon_path(cx, cy, r, p):
    """Lit part of the moon; p from 0 (new moon) via 0.5 (full moon) to 1."""
    k = math.cos(2 * math.pi * p)
    rx = abs(k) * r
    waxing = p < .5
    outer = 1 if waxing else 0
    inner = (0 if waxing else 1) if k > 0 else (1 if waxing else 0)
    return (f'M{cx} {cy - r} A{r} {r} 0 0 {outer} {cx} {cy + r} '
            f'A{num(rx)} {r} 0 0 {inner} {cx} {cy - r} Z')


def quay_wall(p, drop):
    """The quay wall the falling tide bares: dark like the city, wet and green towards the water."""
    sc, sop = p['shimmer']
    top, bottom = BASE, BASE + drop
    return (f'<linearGradient id="tide-wet" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3f5c3a" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="#3f5c3a" stop-opacity=".45"/></linearGradient>'
            f'<rect y="{top}" width="{W}" height="{drop}" fill="{p["near"]}"/>'
            f'<rect y="{top}" width="{W}" height="{drop}" fill="url(#tide-wet)"/>'
            f'<rect y="{bottom - 1}" width="{W}" height="1" fill="{sc}" fill-opacity="{num(sop * .45)}"/>')


def compose(name, animated, wind='calm', direction=1, moon=None, tide=None, css='', defs='', behind_city='',
            city_back='', city_front='', glass='', heat_shimmer=False, ferry='', rock=False, overlay=''):
    """The whole scene as SVG text. moon: 0..7 (eight phases) or None; tide: 0..4 (low to high) or None."""
    p = PALETTES[name]
    drop = (TIDE_STEPS - tide) * TIDE_DROP if tide is not None else 0
    water = BASE + drop
    rng = random.Random(name)
    speed = {'calm': 1, 'windy': 3, 'storm': 7}[wind]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">']
    if animated:
        out.append(f'<style>{c.BASE_CSS}{css}</style>')
    wc = p['win']
    out.append('<defs>' + c.gradient('sky', p['sky']) + c.gradient('water', p['water']) +
               f'<pattern id="quay" width="7" height="8" patternUnits="userSpaceOnUse"><rect x="2" y="2" width="2.4" height="3.4" fill="{wc}"/></pattern>'
               '<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0.34"/><stop offset="0.75" stop-color="#fff" stop-opacity="0"/></linearGradient>'
               f'<mask id="refl"><rect x="0" y="{water}" width="{W}" height="190" fill="url(#fade)"/></mask>'
               '<filter id="blur" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="1.3"/></filter>'
               '<radialGradient id="sun"><stop offset="0" stop-color="#fffbe8"/><stop offset=".55" stop-color="#ffe590"/><stop offset="1" stop-color="#ffd262"/></radialGradient>'
               '<radialGradient id="sunglow"><stop offset="0" stop-color="#ffde82" stop-opacity=".6"/><stop offset="1" stop-color="#ffde82" stop-opacity="0"/></radialGradient>'
               '<radialGradient id="dusk-sun"><stop offset="0" stop-color="#ffe4ae"/><stop offset=".5" stop-color="#ffb062"/><stop offset="1" stop-color="#ef7a4b"/></radialGradient>'
               '<radialGradient id="dusk-glow"><stop offset="0" stop-color="#ff9650" stop-opacity=".5"/><stop offset="1" stop-color="#ff9650" stop-opacity="0"/></radialGradient>'
               + defs + '</defs>')
    out.append(f'<rect width="{W}" height="{BASE}" fill="url(#sky)"/>')
    if p.get('stars'):
        g = []
        for _ in range(170):
            x, y, r = rng.uniform(0, W), rng.uniform(0, 300), rng.uniform(.5, 1.2)
            st = (f' class="star" style="animation-duration:{rng.uniform(2, 6):.1f}s;animation-delay:-{rng.uniform(0, 5):.1f}s"'
                  if animated else f' opacity="{rng.uniform(.3, 1):.2f}"')
            g.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="#fff"{st}/>')
        out.append(''.join(g))
    if p['body'] == 'sun':
        out.append(f'<circle cx="{OX+317}" cy="99" r="80" fill="url(#sunglow)"/><circle cx="{OX+317}" cy="99" r="27" fill="url(#sun)"/>')
    elif p['body'] == 'evening_sun':
        out.append(f'<circle cx="{OX+212}" cy="312" r="150" fill="url(#dusk-glow)"/><circle cx="{OX+212}" cy="312" r="62" fill="url(#dusk-sun)"/>')
    elif p['body'] == 'moon':
        if moon is None:
            out.append(f'<circle cx="{OX+312}" cy="98" r="30" fill="{MOON_COLOR}" opacity=".12"/>'
                       f'<path d="M{OX+318} 80 A20 20 0 1 0 {OX+330} 112 A16 16 0 0 1 {OX+318} 80 Z" fill="{MOON_COLOR}"/>')
        else:
            phase = moon / 8
            lit = (1 - math.cos(2 * math.pi * phase)) / 2
            out.append(f'<circle cx="{OX+312}" cy="98" r="30" fill="{MOON_COLOR}" opacity="{num(.05 + .17 * lit)}"/>'
                       f'<circle cx="{OX+314}" cy="97" r="18" fill="{MOON_COLOR}" opacity=".07"/>'
                       f'<path d="{moon_path(OX+314, 97, 18, phase)}" fill="{MOON_COLOR}"/>')
    if p['clouds']:
        color, op, n = p['clouds']
        g = []
        for _ in range(n):
            w = rng.uniform(180, 340)
            y = rng.uniform(-10, 170)
            s = w / 200
            if animated:
                dur = rng.uniform(110, 240)
                delay = rng.uniform(0, dur)
                reverse = ';animation-direction:reverse' if direction < 0 else ''
                g.append(f'<g class="drift" style="animation-duration:{dur / speed:.1f}s;animation-delay:-{delay / speed:.1f}s{reverse}">'
                         f'<g transform="translate(0 {y:.0f}) scale({s:.2f})" opacity="{op}">{c.cloud(color)}</g></g>')
            else:
                x = rng.uniform(-100, W)
                g.append(f'<g transform="translate({x:.0f} {y:.0f}) scale({s:.2f})" opacity="{op}">{c.cloud(color)}</g>')
        out.append(''.join(g))
    out.append(behind_city)
    town = c.city(p, rng)
    if city_back:
        i = town.index(f'\n<path fill="{p["near"]}"')
        town = town[:i] + city_back + town[i:]
    if glass:
        i = town.index(f'<path fill="{p["glass"]}" d="M{OX+70} 128')
        j = town.index('/>', i) + 2
        town = town[:j] + glass + town[j:]
    if city_front:
        i = town.rindex('</g>')
        town = town[:i] + city_front + town[i:]
    filt = ' filter="url(#fx-heat)"' if heat_shimmer and animated else ''
    out.append(f'<g transform="translate(0 {SKY_TOP})"{filt}>{town}</g>')
    out.append(f'<rect y="{BASE}" width="{W}" height="{H-BASE}" fill="url(#water)"/>')
    out.append(f'<g mask="url(#refl)" filter="url(#blur)"><use href="#city" transform="translate(0 {water*2 - SKY_TOP}) scale(1 -1)"/></g>')
    sc, sop = p['shimmer']
    if drop:
        out.append(quay_wall(p, drop))
    g = []
    for _ in range(70):
        x, y, w = rng.uniform(0, W), rng.uniform(BASE + 8, BASE + 200) + drop, rng.uniform(10, 40)
        st = (f' class="shimmer" style="animation-duration:{rng.uniform(3, 6):.1f}s;animation-delay:-{rng.uniform(0, 4):.1f}s"'
              if animated else f' opacity="{rng.uniform(.15, .6):.2f}"')
        g.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="1.5" rx=".75" fill="{sc}" fill-opacity="{sop}"{st}/>')
    out.append(''.join(g))
    hull = (f'<g fill="{p["near"]}"><path d="M2 10 H44 L40 15 H6 Z"/><path d="M12 5 H31 V10 H12 Z"/><path d="M10 4 H33 V5.2 H10 Z"/>'
            f'<path d="M34 3 H37 V10 H34 Z"/></g><g fill="{wc}" opacity="{p["win_op"]}"><rect x="14" y="6.5" width="3" height="2"/>'
            f'<rect x="19.5" y="6.5" width="3" height="2"/><rect x="25" y="6.5" width="3" height="2"/></g>' + ferry)
    if rock and animated:
        hull = f'<g class="fx-rock">{hull}</g>'
    if animated:
        out.append(f'<g class="ship"><g transform="translate(0 {water+4})">{hull}</g></g>')
    else:
        out.append(f'<g transform="translate({OX+40} {water+4})">{hull}</g>')
    angle = -direction * {'calm': 9, 'windy': 22, 'storm': 36}[wind]
    if p.get('rain'):
        g = []
        factor = 1.35 if wind == 'storm' else 1
        for _ in range(260):
            x, ln = rng.uniform(-150, W + 150), rng.uniform(12, 24)
            op = rng.uniform(.2, .55)
            if animated:
                g.append(f'<rect class="drop" x="{x:.0f}" y="-40" width="1.3" height="{ln:.0f}" fill="#e8f0fa" opacity="{op:.2f}" '
                         f'style="animation-duration:{rng.uniform(.55, .9) / factor:.2f}s;animation-delay:-{rng.uniform(0, 1.5):.2f}s"/>')
            else:
                g.append(f'<rect x="{x:.0f}" y="{rng.uniform(-40, H):.0f}" width="1.3" height="{ln:.0f}" fill="#e8f0fa" opacity="{op:.2f}"/>')
        out.append(f'<g transform="translate({W/2:.0f} {H/2:.0f}) rotate({angle}) scale(1.3) translate(-{W/2:.0f} -{H/2:.0f})">{"".join(g)}</g>')
    if p.get('snow'):
        g = []
        factor = {'calm': 1, 'windy': 1.5, 'storm': 2.4}[wind]
        for _ in range(200):
            x, r = rng.uniform(0, W), rng.uniform(1, 2.6)
            op = rng.uniform(.55, .95)
            if animated:
                g.append(f'<circle class="flake" cx="{x:.0f}" cy="-12" r="{r:.1f}" fill="#fff" opacity="{op:.2f}" '
                         f'style="animation-duration:{rng.uniform(7, 15) / factor:.1f}s;animation-delay:-{rng.uniform(0, 15):.1f}s"/>')
            else:
                g.append(f'<circle cx="{x:.0f}" cy="{rng.uniform(0, H):.0f}" r="{r:.1f}" fill="#fff" opacity="{op:.2f}"/>')
        if wind == 'calm':
            out.append(''.join(g))
        else:
            slant = -direction * (48 if wind == 'storm' else 24)
            out.append(f'<g transform="translate({W/2:.0f} {H/2:.0f}) rotate({slant}) scale(1.4) translate(-{W/2:.0f} -{H/2:.0f})">{"".join(g)}</g>')
    out.append(overlay)
    out.append('</svg>')
    return '\n'.join(out)
