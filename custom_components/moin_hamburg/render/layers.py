"""Layers over the base scene: season, wind, extremes and special days.

Every function returns SVG text. Motion uses CSS classes with the fx- prefix
whose parameters sit as CSS variables in the style attribute; the still image
has no stylesheet, and move() puts each part at its starting position.

layers(ctx, palette) returns the fragments for scene.compose().
"""
import math
import random

from .city import CRANES
from .palette import BASE, H, OX, TIDE_DROP, TIDE_STEPS, W
from .scene import num

LAYER_CSS = """
.fx-fly{animation:fx-fly var(--d) linear var(--dl) infinite}
.fx-hover{animation:fx-fly var(--d) ease-in-out var(--dl) infinite alternate}
@keyframes fx-fly{from{transform:translate(var(--x0),var(--y0))}to{transform:translate(var(--x1),var(--y1))}}
.fx-sway{animation:fx-sway var(--sd) ease-in-out infinite alternate}
@keyframes fx-sway{from{transform:translateX(calc(var(--sw) * -1))}to{transform:translateX(var(--sw))}}
.fx-bob{animation:fx-bob var(--bd) ease-in-out infinite alternate}
@keyframes fx-bob{from{transform:translateY(calc(var(--ba) * -1))}to{transform:translateY(var(--ba))}}
.fx-spin{transform-box:fill-box;transform-origin:center;animation:fx-spin var(--rd) linear infinite}
@keyframes fx-spin{0%{transform:rotate(0deg) scaleX(1)}50%{transform:rotate(180deg) scaleX(-.35)}100%{transform:rotate(360deg) scaleX(1)}}
.fx-flap{transform-box:fill-box;transform-origin:center;animation:fx-flap var(--fd) ease-in-out infinite alternate}
@keyframes fx-flap{from{transform:scaleY(1)}to{transform:scaleY(-.55)}}
.fx-heel{transform-box:fill-box;transform-origin:50% 100%;animation:fx-heel var(--kd) ease-in-out infinite alternate}
@keyframes fx-heel{from{transform:rotate(calc(var(--h) - 3deg))}to{transform:rotate(calc(var(--h) + 2deg))}}
.fx-rock{transform-box:fill-box;transform-origin:50% 100%;animation:fx-rock 2.1s ease-in-out infinite alternate}
@keyframes fx-rock{from{transform:rotate(-3.5deg)}to{transform:rotate(3deg) translateY(1.5px)}}
.fx-foam{animation:fx-foam var(--sd) ease-out var(--dl) infinite}
@keyframes fx-foam{0%{opacity:0;transform:translateX(0)}25%{opacity:.85}55%{opacity:0;transform:translateX(var(--dx))}100%{opacity:0;transform:translateX(var(--dx))}}
.fx-firefly{animation:fx-firefly var(--gd) ease-in-out var(--dl) infinite}
@keyframes fx-firefly{0%,100%{opacity:0}40%,60%{opacity:1}}
.fx-twinkle{animation:fx-twinkle var(--fd) ease-in-out var(--dl) infinite alternate}
@keyframes fx-twinkle{from{opacity:.3}to{opacity:1}}
.fx-lamp{animation:fx-lamp 1.6s ease-in-out infinite}
@keyframes fx-lamp{0%,100%{opacity:.2}50%{opacity:1}}
.fx-flutter{animation:fx-flutter var(--fd) ease-in-out infinite alternate}
@keyframes fx-flutter{from{transform:rotate(calc(var(--fa) * -1))}to{transform:rotate(var(--fa))}}
.fx-bolt{opacity:0;animation:fx-bolt var(--bd) linear var(--dl) infinite}
@keyframes fx-bolt{0%,90%,95%,100%{opacity:0}91%,94%{opacity:1}92.5%{opacity:.25}}
.fx-flash{opacity:0;animation:fx-flash var(--bd) linear var(--dl) infinite}
@keyframes fx-flash{0%,90%,95%,100%{opacity:0}91%,94%{opacity:.3}92.5%{opacity:.08}}
.fx-burst{animation:fx-burst var(--bd) ease-out var(--dl) infinite}
@keyframes fx-burst{0%{transform:scale(.05);opacity:0}4%{opacity:1}36%{transform:scale(1);opacity:.95}55%{transform:scale(1.06) translateY(7px);opacity:0}100%{transform:scale(1.06) translateY(7px);opacity:0}}
.fx-steam{transform-box:fill-box;transform-origin:center;animation:fx-steam 3.4s ease-out var(--dl) infinite}
@keyframes fx-steam{0%{transform:translate(0,0) scale(.4);opacity:0}12%{opacity:.75}100%{transform:translate(var(--dx),-28px) scale(2.6);opacity:0}}
.fx-swell{animation:fx-swell 3.6s ease-in-out infinite alternate}
@keyframes fx-swell{from{transform:translate(-14px,1px)}to{transform:translate(14px,-1.5px)}}
.fx-pulse{animation:fx-pulse 7s ease-in-out infinite alternate}
@keyframes fx-pulse{from{opacity:.55}to{opacity:.9}}
.fx-hop{animation:fx-hop .6s ease-in-out infinite}
@keyframes fx-hop{0%,100%{transform:translateY(0)}45%{transform:translateY(-7px)}}
.fx-flicker{transform-box:fill-box;transform-origin:50% 100%;animation:fx-flicker var(--fd) ease-in-out infinite alternate}
@keyframes fx-flicker{0%{transform:scale(1,1) skewX(0deg)}50%{transform:scale(.9,1.14) skewX(5deg)}100%{transform:scale(1.06,.88) skewX(-4deg)}}
.fx-spark{animation:fx-spark var(--d) linear var(--dl) infinite}
@keyframes fx-spark{0%{transform:translate(0,0);opacity:1}100%{transform:translate(var(--dx),-70px);opacity:0}}
.fx-meteor{opacity:0;animation:fx-meteor var(--d) ease-in var(--dl) infinite}
@keyframes fx-meteor{0%{transform:translate(0,0);opacity:0}1%{opacity:1}7%{transform:translate(150px,52px);opacity:0}100%{transform:translate(150px,52px);opacity:0}}
.fx-turn{animation:fx-turn 40s linear infinite}
@keyframes fx-turn{to{transform:rotate(360deg)}}
.fx-glimmer{animation:fx-glimmer var(--fd) steps(2) infinite alternate}
@keyframes fx-glimmer{from{opacity:.6}to{opacity:1}}
@media (prefers-reduced-motion: reduce){[class^="fx-"]{animation:none!important}}
"""


class Context:
    """The parsed state, plus the random source and the animation switch."""

    def __init__(self, tod, weather, season, wind, direction, moon, extremes, warning, day, animated, seed, tide=None,
                 ships=()):
        self.tod, self.weather, self.season, self.wind = tod, weather, season, wind
        self.water = BASE + ((TIDE_STEPS - tide) * TIDE_DROP if tide is not None else 0)  # the waterline
        self.ships = set(ships)
        self.dir, self.moon, self.extremes = direction, moon, set(extremes)
        self.warning, self.day, self.animated = warning, day, animated
        self.rng = random.Random(seed)
        self.night = tod == 'night'

    def uniform(self, a, b):
        return a + (b - a) * self.rng.random()

    def pick(self, items):
        return items[int(self.rng.random() * len(items))]


def move(ctx, x0, y0, x1, y1, d, dl, inner, hover=False):
    """Motion from (x0,y0) to (x1,y1) in d seconds; the still image shows the starting point."""
    if ctx.animated:
        cls = 'fx-hover' if hover else 'fx-fly'
        return (f'<g class="{cls}" style="--x0:{num(x0)}px;--y0:{num(y0)}px;--x1:{num(x1)}px;--y1:{num(y1)}px;'
                f'--d:{num(d)}s;--dl:{num(dl)}s">{inner}</g>')
    t = ((-dl) % d) / d if d else 0
    return f'<g transform="translate({num(x0 + (x1 - x0) * t)} {num(y0 + (y1 - y0) * t)})">{inner}</g>'


# --- Particles: leaves, blossoms, confetti ------------------------------------
LEAF = ['M0 -6 L2 -2 L6 -3 L4 1 L6 3 L1 3 L0 7 L-1 3 L-6 3 L-4 1 L-6 -3 L-2 -2 Z',
        'M0 -6 C4 -4 4 4 0 7 C-4 4 -4 -4 0 -6 Z', 'M0 -5 C5 -5 5 3 0 6 C-1 3 -3 0 0 -5 Z']
BLOSSOM = ['M-3 0 C-3 -2 3 -2 3 0 C3 2 -3 2 -3 0 Z', 'M-2.6 -.4 C-2 -2.2 2.4 -1.6 2.8 0 C2.2 1.8 -2 2 -2.6 .4 Z']
CONFETTI = ['M-1.8 -1 H1.8 V1 H-1.8 Z', 'M-1 -1.8 H1 V1.8 H-1 Z', 'M0 -1.4 A1.4 1.4 0 1 1 0 1.4 A1.4 1.4 0 1 1 0 -1.4 Z']


def drifters(ctx, n, wind, colors, shapes, size, opacity, speed=1):
    """Particles carried by the wind: falling gently, blown across, or swept in a storm."""
    s = []
    u = ctx.uniform
    for _ in range(n):
        if wind == 'calm':
            x0, y0 = u(-50, 1250), u(-60, -20)
            x1, y1 = x0 + ctx.dir * u(-30, 140), u(880, 930)
            d, sw, sd, rd = u(13, 22) * speed, u(14, 30), u(2.2, 3.8), u(4, 8)
        elif wind == 'windy':
            x0 = u(-550, 1000) if ctx.dir > 0 else u(200, 1750)
            y0 = u(-60, -20)
            x1, y1 = x0 + ctx.dir * u(650, 950), u(880, 940)
            d, sw, sd, rd = u(6.5, 10) * speed, u(8, 16), u(1.6, 2.6), u(1.8, 3.2)
        else:
            x0 = u(-320, -40) if ctx.dir > 0 else u(1240, 1520)
            y0 = u(-40, 760)
            x1, y1 = x0 + ctx.dir * u(1500, 1800), y0 + u(-120, 220)
            d, sw, sd, rd = u(2, 3.6), u(4, 10), u(.8, 1.4), u(.6, 1.3)
        dl, g = -u(0, d), u(size[0], size[1])
        inner = (f'<g class="fx-sway" style="--sw:{num(sw)}px;--sd:{num(sd)}s"><g transform="scale({num(g)})">'
                 f'<path class="fx-spin" style="--rd:{num(rd)}s" d="{ctx.pick(shapes)}" fill="{ctx.pick(colors)}" opacity="{opacity}"/></g></g>')
        s.append(move(ctx, x0, y0, x1, y1, d, dl, inner))
    return ''.join(s)


def rising(ctx, n, y, d, size, colors, shape):
    """Things floating up from the water: hearts, balloons."""
    s = []
    u = ctx.uniform
    for _ in range(n):
        x0, y0, dd, g = u(-40, 1240), u(*y), u(*d), u(*size)
        inner = (f'<g class="fx-sway" style="--sw:{num(u(6, 16))}px;--sd:{num(u(2.4, 4.2))}s">'
                 f'<g transform="scale({num(g)})">{shape(ctx.pick(colors))}</g></g>')
        s.append(move(ctx, x0, y0, x0 + ctx.dir * u(20, 90), -60, dd, -u(0, dd), inner))
    return ''.join(s)


# --- Birds --------------------------------------------------------------------
def gulls(ctx):
    if ctx.night:
        return ''
    u = ctx.uniform
    color = '#f4f6f8' if ctx.tod == 'day' else '#ead8cf'
    s = []
    for _ in range({'calm': 7, 'windy': 6, 'storm': 3}[ctx.wind]):
        y = u(50, 250)
        if ctx.wind == 'storm':
            x0 = u(390, 810)
            x1, d, hover = x0 - ctx.dir * u(60, 140), u(6, 10), True
        else:
            x0, x1 = (-60, 1260) if ctx.dir > 0 else (1260, -60)
            d, hover = (u(34, 52) if ctx.wind == 'calm' else u(16, 24)), False
        inner = (f'<g class="fx-bob" style="--ba:{num(u(2, 9 if ctx.wind == "storm" else 4))}px;--bd:{num(u(1.2, 2.4))}s">'
                 f'<path class="fx-flap" style="--fd:{num(u(.22, .42))}s" d="M-7 0 Q-3.5 -4 0 0 Q3.5 -4 7 0" fill="none" '
                 f'stroke="{color}" stroke-width="1.4" stroke-linecap="round"/></g>')
        s.append(move(ctx, x0, y, x1, y + u(-30, 30), d, -u(0, d), inner, hover))
    return ''.join(s)


def migrating_birds(ctx, direction):
    """A V of birds: northbound in spring, southbound in autumn."""
    if ctx.night:
        return ''
    color = '#26313e' if ctx.tod == 'day' else '#2b2232'
    v = ''.join(f'<g transform="translate({dx * direction} {dy})"><path class="fx-flap" style="--fd:{num(ctx.uniform(.45, .75))}s" '
                f'd="M-4.5 0 Q-2.2 -2.8 0 0 Q2.2 -2.8 4.5 0" fill="none" stroke="{color}" stroke-width="1.3" stroke-linecap="round"/></g>'
                for dx, dy in [(0, 0), (-11, -6), (-22, -12), (-33, -18), (-44, -24), (-11, 6), (-22, 12), (-33, 18)])
    y = ctx.uniform(70, 120)
    x0, x1 = (-250, 1450) if direction > 0 else (1450, -250)
    return move(ctx, x0, y, x1, y - 30, 58, -58 * .45, v)


# --- Water --------------------------------------------------------------------
def sailboats(ctx, near):
    if ctx.night or ctx.wind == 'storm':
        return ''
    u = ctx.uniform
    heel = 4 if ctx.wind == 'calm' else 14
    s = []
    for _ in range(3 if ctx.wind == 'calm' else 4):
        y = u(352, 470)
        g = .55 + .45 * (y - 352) / 118
        d = u(170, 250) if ctx.wind == 'calm' else u(80, 120)
        x0, x1 = (-80, 1280) if ctx.dir > 0 else (1280, -80)
        inner = (f'<g transform="scale({num(g * ctx.dir)} {num(g)})"><g class="fx-heel" style="--h:{heel}deg;--kd:{num(u(2.5, 4))}s">'
                 f'<path d="M-10 0 H10 L7 4 H-7 Z" fill="{near}"/><path d="M0 -1 V-26" stroke="{near}" stroke-width="1"/>'
                 f'<path d="M1 -2 V-25 L14 -3 Z" fill="#f4f6f8" opacity=".93"/><path d="M-1 -4 V-20 L-9 -4 Z" fill="#e3e9f0" opacity=".85"/></g></g>')
        s.append(move(ctx, x0, y, x1, y, d, -u(0, d), inner))
    return ''.join(s)


def whitecaps(ctx, n):
    u = ctx.uniform
    color = '#9fadc0' if ctx.night else '#f4f8fc'
    s = []
    for _ in range(n):
        y = u(338, 800)
        g, x, sd = .5 + (y - 338) / 462 * 1.3, u(0, 1200), u(2.5, 5)
        op = '' if ctx.animated else f' opacity="{num(u(.2, .7))}"'
        s.append(f'<g transform="translate({num(x)} {num(y)}) scale({num(g)})"><path class="fx-foam" style="--sd:{num(sd)}s;--dl:-{num(u(0, sd))}s;'
                 f'--dx:{ctx.dir * 14}px" d="M-6 0 Q0 -3 6 0" fill="none" stroke="{color}" stroke-width="1.3" stroke-linecap="round"{op}/></g>')
    return ''.join(s)


def ice_floes(ctx):
    u = ctx.uniform
    color, stroke = ('#7a879f', '#5a6680') if ctx.night else ('#e4eef8', '#b6c8da')
    s = []
    for _ in range(24):
        y = u(338, 720)
        g, w = .45 + (y - 338) / 382 * 1.4, u(14, 40)
        h = w * u(.18, .3)
        points = ' '.join(f'{num(math.cos(j / 7 * 2 * math.pi) * w / 2 * q)},{num(math.sin(j / 7 * 2 * math.pi) * h / 2 * q)}'
                          for j, q in ((j, u(.75, 1.1)) for j in range(7)))
        x0, d = u(1250, 1450), u(160, 260)
        inner = f'<g transform="scale({num(g)})"><polygon points="{points}" fill="{color}" stroke="{stroke}" stroke-width=".8" opacity=".9"/></g>'
        s.append(move(ctx, x0, y, x0 - 1700, y, d, -u(0, d), inner))
    return ''.join(s)


def pack_ice(ctx):
    """Ice drift: after days of hard frost the Elbe carries pack ice downstream, and ice rims the quay wall.

    One group of floes, drawn twice a picture-width apart, drifts left by one width: the loop has no seam
    and costs a single moving part. Its keyframes come along, so pictures without ice keep their CSS.
    """
    u = ctx.uniform
    color, stroke = ('#7d8aa3', '#5a6680') if ctx.night else ('#eef4fa', '#b6c8da')
    top = ctx.water
    floes = []
    for _ in range(130):
        y = top + 5 + (720 - top - 5) * ctx.rng.random() ** 1.8   # crowded towards the far bank
        g, w = .45 + (y - 338) / 382 * 1.4, u(22, 64)
        h = w * u(.2, .32)
        points = ' '.join(f'{num(math.cos(j / 8 * 2 * math.pi) * w / 2 * q)},{num(math.sin(j / 8 * 2 * math.pi) * h / 2 * q)}'
                          for j, q in ((j, u(.7, 1.1)) for j in range(8)))
        x = u(0, W)
        floe = f'<polygon points="{points}" fill="{color}" stroke="{stroke}" stroke-width=".8" opacity="{num(u(.8, .95))}"/>'
        floes += [f'<g transform="translate({num(x + dx)} {num(y)}) scale({num(g)})">{floe}</g>' for dx in (0, W)]
    drift = ''.join(floes)
    if ctx.animated:
        drift = (f'<style>.fx-icedrift{{animation:fx-icedrift var(--d) linear infinite}}'
                 f'@keyframes fx-icedrift{{from{{transform:translateX(0)}}to{{transform:translateX(-{W}px)}}}}</style>'
                 f'<g class="fx-icedrift" style="--d:{num(u(700, 900))}s">{drift}</g>')
    rim = [f'M0 {top - 1} H{W} V{top + 2}']
    x = W
    while x > 0:
        x -= u(8, 22)
        rim.append(f'L{num(max(x, 0))} {num(top + u(2, 6))}')
    rim.append('Z')
    return (f'<g>{drift}</g><path d="{" ".join(rim)}" fill="{color}" stroke="{stroke}" stroke-width=".6"/>')


def _mirrored(fragment, waterline, opacity=.2):
    """The fragment and its reflection below the waterline."""
    return f'{fragment}<g transform="matrix(1 0 0 -1 0 {num(2 * waterline)})" opacity="{opacity}">{fragment}</g>'


def cruise_ship(ctx):
    """A cruise ship lying at the terminal right of the Michel, bow to the east; lit decks after dark."""
    hull, window, window_op = {'day': ('#f3f6f9', '#3a4a60', .5), 'dusk': ('#ddd3d8', '#ffd59a', .85),
                               'night': ('#8d97a8', '#ffd27a', 1)}[ctx.tod]
    s = (f'<path d="M0 -26 H214 L232 -31 L222 0 H6 Z" fill="{hull}"/>'
         '<path d="M6 0 L2 -8 H228 L222 0 Z" fill="#1f2f4a"/>'
         f'<path d="M14 -26 V-44 H206 V-26 Z M22 -44 V-57 H196 V-44 Z M36 -57 V-68 H178 V-57 Z" fill="{hull}"/>'
         '<path d="M14 -44 H206 M22 -57 H196" stroke="#000" stroke-opacity=".12" stroke-width="1"/>'
         '<path d="M96 -68 L100 -86 H120 L123 -68 Z" fill="#2a3446"/><rect x="99" y="-82" width="22" height="3" fill="#c9d3e0"/>')
    rows = ''.join(f'<rect x="{x}" y="{y}" width="3" height="2"/>'
                   for y, x0, x1 in ((-37, 20, 202), (-51, 28, 192), (-63, 42, 174), (-18, 12, 210))
                   for x in range(x0, x1, 6))
    s += f'<g fill="{window}" opacity="{window_op}">{rows}</g>'
    s += ''.join(f'<ellipse cx="{x}" cy="-45" rx="4.2" ry="2" fill="#ff8a3d"/>' for x in range(30, 196, 15))
    return _mirrored(f'<g transform="translate({OX + 252} {num(ctx.water + 2)}) scale(.92)">{s}</g>', ctx.water + 2)


def container_ship(ctx):
    """A big container ship under way, bow first upstream into the harbour, slowly crossing the near fairway."""
    u = ctx.uniform
    dim = .55 if ctx.night else .8 if ctx.tod == 'dusk' else 1
    colours = ['#c0392b', '#2e86c1', '#27ae60', '#d68910', '#7f8c8d', '#884ea0', '#1f618d', '#a04000']
    boxes = []
    for x in range(44, 284, 11):
        for tier in range(int(u(3, 6))):
            boxes.append(f'<rect x="{x}" y="{-20 - tier * 6}" width="10" height="5.6" fill="{ctx.pick(colours)}"/>')
    s = (f'<g opacity="{dim}">{"".join(boxes)}</g>'
         '<path d="M0 -14 H292 L302 -19 L294 0 H8 Z" fill="#2d3a48"/><path d="M8 0 L4 -5 H297 L294 0 Z" fill="#8a2a24"/>'
         '<path d="M10 -14 V-46 H36 V-14 Z" fill="#e8ecf0"/><path d="M8 -46 H38 V-50 H8 Z" fill="#d4dae1"/>'
         '<path d="M18 -50 V-58 H28 V-50 Z" fill="#2a3446"/>')
    if ctx.tod != 'day':
        s += ('<g fill="#ffd27a">' + ''.join(f'<rect x="{x}" y="-42" width="3" height="2"/>' for x in range(13, 34, 5)) + '</g>'
              '<circle cx="23" cy="-60" r="1.4" fill="#fff"/><circle cx="300" cy="-20" r="1.3" fill="#ff5a4f"/>')
    y = ctx.water + 20
    inner = f'<g transform="scale(.78)">{_mirrored(s, 0, .18)}</g>'
    d, dl = u(600, 760), -u(0, 600)
    if not ctx.animated:
        dl = -d * .6  # the still image shows it in front of the cranes
    return move(ctx, -300, y, 1400, y, d, dl, inner)


def storm_surge(ctx, water_color):
    """The Elbe rises over the quay."""
    level = BASE - 13
    d = f'M-60 {level}' + ''.join(' q7.5 -3 15 0 t15 0' for _ in range(-60, 1260, 30))
    edge = d
    d += f' V{BASE + 40} H-60 Z'
    line = '#8090a8' if ctx.night else '#e8f0f8'
    return (f'<defs><linearGradient id="fx-surge" gradientUnits="userSpaceOnUse" x1="0" y1="{level - 4}" x2="0" y2="{BASE + 40}">'
            f'<stop offset="0" stop-color="{water_color}" stop-opacity=".97"/><stop offset=".7" stop-color="{water_color}" stop-opacity=".9"/>'
            f'<stop offset="1" stop-color="{water_color}" stop-opacity="0"/></linearGradient></defs>'
            f'<g class="fx-swell"><path d="{d}" fill="url(#fx-surge)"/><path d="{edge}" fill="none" stroke="{line}" stroke-width="1" opacity=".45"/></g>')


def fireflies(ctx):
    u = ctx.uniform
    s = []
    for _ in range(28):
        x, y, gd = u(0, 1200), u(292, 400), u(2, 5)
        s.append(f'<g transform="translate({num(x)} {num(y)})"><g class="fx-sway" style="--sw:{num(u(6, 14))}px;--sd:{num(u(2.5, 5))}s">'
                 f'<circle r="{num(u(1, 1.8))}" fill="#fff3a0" filter="url(#fx-glow)" class="fx-firefly" style="--gd:{num(gd)}s;--dl:-{num(u(0, gd))}s"/></g></g>')
    return ''.join(s)


# --- Sky ----------------------------------------------------------------------
def gust_streaks(ctx):
    u = ctx.uniform
    color = 'rgba(200,215,235,.2)' if ctx.night else 'rgba(255,255,255,.38)'
    s = []
    for _ in range(12):
        y, length = u(20, 300), u(90, 180)
        x0 = u(-2600, -300) if ctx.dir > 0 else u(1500, 3800)
        d = u(3, 5)
        inner = (f'<path d="M0 0 q{num(length / 2 * ctx.dir)} {num(-u(3, 9))} {num(length * ctx.dir)} 0" '
                 f'stroke="{color}" stroke-width="1.1" fill="none" stroke-linecap="round"/>')
        s.append(move(ctx, x0, y, x0 + ctx.dir * 3000, y + u(-20, 20), d, -u(0, d), inner))
    return ''.join(s) if ctx.animated else ''


def fog(ctx):
    u = ctx.uniform
    color = {'day': '#d9dfe5', 'dusk': '#bcaab6', 'night': '#323a4b'}[ctx.tod]
    s = (f'<defs><linearGradient id="fx-fog" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{color}" stop-opacity=".25"/>'
         f'<stop offset=".3" stop-color="{color}" stop-opacity=".55"/><stop offset=".39" stop-color="{color}" stop-opacity=".84"/>'
         f'<stop offset=".55" stop-color="{color}" stop-opacity=".55"/><stop offset="1" stop-color="{color}" stop-opacity=".35"/></linearGradient>'
         '<filter id="fx-soft" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="18"/></filter></defs>'
         f'<rect width="{W}" height="{H}" fill="url(#fx-fog)"/>')
    for _ in range(7):
        y, w, h, x0, d = u(180, 520), u(260, 520), u(26, 60), u(-300, 1200), u(40, 80)
        inner = f'<ellipse rx="{num(w / 2)}" ry="{num(h / 2)}" fill="{color}" opacity=".55" filter="url(#fx-soft)"/>'
        s += move(ctx, x0, y, x0 + u(200, 420), y, d, -u(0, d), inner, True)
    return s


def lightning(ctx):
    if not ctx.animated:
        return ''
    u = ctx.uniform
    s = []
    for n in range(2):
        x = u(440, 760)
        y, px, d, branch = 0, x, f'M{num(x)} 0', ''
        while y < BASE - 70:
            y += u(14, 30)
            px += u(-14, 14)
            d += f' L{num(px)} {num(y)}'
            if not branch and y > 110:
                bx, by = px, y
                branch = f'M{num(bx)} {num(by)}'
                for _ in range(4):
                    by += u(10, 20)
                    bx += u(4, 16) * (1 if n else -1)
                    branch += f' L{num(bx)} {num(by)}'
        bd = u(6, 10)
        dl = -u(0, bd)
        s.append(f'<rect width="{W}" height="{BASE}" fill="#e9eeff" class="fx-flash" style="--bd:{num(bd)}s;--dl:{num(dl)}s"/>'
                 f'<path class="fx-bolt" style="--bd:{num(bd)}s;--dl:{num(dl)}s" d="{d} {branch}" fill="none" stroke="#f6f8ff" stroke-width="2" '
                 f'stroke-linejoin="round" filter="url(#fx-glow2)"/>')
    return ''.join(s)


def fireworks(ctx, colors=None):
    colors = colors or ['#ffd27a', '#ff6f6f', '#9fe3ff', '#ffffff', '#c9a2ff', '#8affc1']
    u = ctx.uniform
    s = []
    for i in range(8):
        cx = u(430, 770) if i < 5 else u(60, 1140)
        cy, rad, c, c2, bd = u(50, 220), u(34, 62), ctx.pick(colors), ctx.pick(colors), u(2.8, 4.6)
        dl = -u(0, bd)
        rays = ''
        for j in range(22):
            a = j / 22 * math.pi * 2 + u(-.08, .08)
            length = rad * u(.8, 1.05)
            rays += (f'<path d="M{num(math.cos(a) * length * .25)} {num(math.sin(a) * length * .25)} '
                     f'L{num(math.cos(a) * length)} {num(math.sin(a) * length)}" stroke="{c2 if j % 3 == 0 else c}"/>')
        s.append(f'<g transform="translate({num(cx)} {num(cy)})"><g class="fx-burst" style="--bd:{num(bd)}s;--dl:{num(dl)}s" '
                 f'stroke-width="1.5" stroke-linecap="round" fill="none">{rays}</g></g>')
    s = ''.join(s)
    return s + f'<g transform="matrix(1 0 0 -1 0 {2 * BASE})" opacity=".22">{s}</g>'


def frost_flowers(ctx):
    """Ice crystals growing in from the top and bottom edges."""
    color = '#b9c8e0' if ctx.night else '#eef6ff'
    parts = []

    def branch(x, y, a, length, depth):
        x2, y2 = x + math.cos(a) * length, y + math.sin(a) * length
        parts.append(f'M{num(x)} {num(y)} L{num(x2)} {num(y2)}')
        if depth <= 0 or length < 4:
            return
        for i in range(1, 4):
            t = i / 4
            bx, by, sub = x + (x2 - x) * t, y + (y2 - y) * t, length * (1 - t) * .55
            branch(bx, by, a + 1.05, sub, depth - 1)
            branch(bx, by, a - 1.05, sub, depth - 1)

    for x in [0, 40, 130, 405, 450, 560, 690, 750, 795, 1070, 1160, 1200]:
        branch(x, 0, math.pi / 2 + ctx.uniform(-.7, .7), ctx.uniform(30, 72), 2)
        branch(x, H, -math.pi / 2 + ctx.uniform(-.7, .7), ctx.uniform(40, 84), 2)
    d = ' '.join(parts)
    return (f'<defs><linearGradient id="fx-rime" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{color}" stop-opacity=".2"/>'
            f'<stop offset=".1" stop-color="{color}" stop-opacity="0"/><stop offset=".88" stop-color="{color}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity=".22"/></linearGradient>'
            '<filter id="fx-soft2" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="1.6"/></filter></defs>'
            f'<rect width="{W}" height="{H}" fill="url(#fx-rime)"/>'
            f'<g fill="none" stroke="{color}" stroke-linecap="round"><path d="{d}" stroke-width="2.6" opacity=".14" filter="url(#fx-soft2)"/>'
            f'<path d="{d}" stroke-width=".8" opacity=".6"/></g>'
            f'<rect width="{W}" height="{H}" fill="#cfe3ff" opacity=".07"/>')


def hoarfrost(ctx):
    color = '#c9d4e8' if ctx.night else '#ffffff'
    s = []
    for _ in range(40):
        x, y, fd = ctx.uniform(0, 1200), ctx.pick([323.4, 311.6, 273.8, 285.8]), ctx.uniform(1, 2.6)
        s.append(f'<circle cx="{num(x)}" cy="{y}" r=".9" fill="{color}" class="fx-twinkle" style="--fd:{num(fd)}s;--dl:-{num(ctx.uniform(0, fd))}s"/>')
    return ''.join(s)


def signal_mast(ctx):
    """The storm signal mast at the harbour: windsock always, balls for storm warnings."""
    mx, top = OX + 44, 232
    mast = '#6b778b' if ctx.night else '#d9dee4'
    s = (f'<rect x="{OX + 20}" y="{BASE + 1}" width="52" height="7" rx="1.5" fill="{"#0c111c" if ctx.night else "#1d2733"}"/>'
         f'<path d="M{mx} {BASE + 2} V{top} M{mx - 9} {top + 12} H{mx + 9}" stroke="{mast}" stroke-width="1.6" stroke-linecap="round"/>')
    angle, length = {'calm': 78, 'windy': 30, 'storm': 4}[ctx.wind], 24
    sock = ''
    for i in range(5):
        a, b = i * length / 5, (i + 1) * length / 5
        h0, h1 = 4 - 2.2 * i / 5, 4 - 2.2 * (i + 1) / 5
        sock += f'<path d="M{num(a)} {num(-h0)} L{num(b)} {num(-h1)} L{num(b)} {num(h1)} L{num(a)} {num(h0)} Z" fill="{"#f4f6f8" if i % 2 else "#ff7a2f"}"/>'
    fa = 6 if ctx.wind == 'storm' else 4 if ctx.wind == 'windy' else 2
    fd = .35 if ctx.wind == 'storm' else .8 if ctx.wind == 'windy' else 2.4
    s += (f'<g transform="translate({mx} {top + 2}) scale({ctx.dir} 1) rotate({angle})">'
          f'<g class="fx-flutter" style="--fa:{fa}deg;--fd:{fd}s">{sock}</g></g>')
    if ctx.warning in ('storm-gusts', 'hurricane'):
        s += f'<path d="M{mx + 9} {top + 12} V{top + 15}" stroke="{mast}" stroke-width=".8"/>'
        for i in range(2 if ctx.warning == 'hurricane' else 1):
            s += f'<circle cx="{mx + 9}" cy="{top + 20 + i * 11}" r="5" fill="#0b0f16" stroke="{mast}" stroke-width=".8"/>'
        s += (f'<circle cx="{mx}" cy="{top - 3}" r="7" fill="#ff5a4f" opacity=".3" class="fx-lamp"/>'
              f'<circle cx="{mx}" cy="{top - 3}" r="2.1" fill="#ff5a4f" class="fx-lamp"/>')
    return s


def tall_ship(ctx, near, ghost=False):
    """A three-masted windjammer (harbour birthday), or its ghost (Halloween)."""
    sail = '#c8ffe8' if ghost else '#3c475b' if ctx.night else '#f3f1ea'
    wood = '#9fe8c8' if ghost else near
    m = ''
    for x in (30, 58, 86):
        m += f'<path d="M{x} 20 V-46" stroke="{wood}" stroke-width="1.6"/>'
        for a, b, w in ((-40, -28, 11), (-26, -12, 13), (-10, 6, 15)):
            m += f'<path d="M{x - w} {a} H{x + w} L{x + w + 1} {b} H{x - w - 1} Z" fill="{sail}" opacity="{.7 if ghost else .95}"/>'
        if not ghost:
            m += f'<path d="M{x} -46 L{x + 9} -43 L{x} -40 Z" fill="{ctx.pick(["#ff5a4f", "#ffd262", "#4fa3ff"])}"/>'
    lights = ''.join(f'<circle cx="{x}" cy="24" r=".9" fill="#ffd27a"/>' for x in range(12, 104, 8)) if ctx.night and not ghost else ''
    hull = (f'<path d="M0 20 H114 L106 31 H8 Z" fill="{wood}"/><path d="M114 20 L134 10" stroke="{wood}" stroke-width="1.4"/>'
            f'<path d="M134 10 L86 -46 M0 20 L30 -46" stroke="{wood}" stroke-width=".6" opacity=".7"/>')
    if ghost:
        inner = f'<g class="fx-bob" style="--ba:2px;--bd:3s"><g transform="scale(1.4)" opacity=".36" filter="url(#fx-glow)">{m}{hull}</g></g>'
        return move(ctx, -250, BASE + 36, 1450, BASE + 36, 170, -85, inner)
    return move(ctx, 1350, BASE + 20, -250, BASE + 20, 150, -60, f'<g transform="scale(-1.5 1.5)">{m}{hull}{lights}</g>')


# --- Special days over the scene -------------------------------------------------
HEART = 'M0 3 C-6 -2 -5 -7 -2 -7 C-.8 -7 0 -6 0 -5 C0 -6 .8 -7 2 -7 C5 -7 6 -2 0 3 Z'


def hearts(ctx):
    return rising(ctx, 22, (340, 520), (24, 38), (.8, 1.5), ['#ff5d8f', '#ff8fb1', '#ffc2d4', '#e8336d'],
                  lambda c: f'<path d="{HEART}" fill="{c}" opacity=".88" filter="url(#fx-glow)"/>')


def balloons(ctx):
    return rising(ctx, 16, (320, 420), (28, 42), (1, 1.6), ['#ff5a4f', '#ffd262', '#4fa3ff', '#5fd38d', '#c58bff', '#ff8fb1'],
                  lambda c: (f'<path d="M0 6 q-3 6 1 12 q3 5 -1 9" stroke="#e8eef5" stroke-width=".5" fill="none" opacity=".7"/>'
                             f'<ellipse rx="4.2" ry="5.4" fill="{c}"/><path d="M-1 5.2 L1 5.2 L0 6.6 Z" fill="{c}"/>'
                             '<ellipse cx="-1.4" cy="-2" rx="1" ry="1.6" fill="#fff" opacity=".35"/>'))


def hare(ctx):
    if ctx.night:
        return ''
    c = '#c9a27a' if ctx.tod == 'day' else '#8f7360'
    body = (f'<ellipse cx="0" cy="-4" rx="6" ry="4" fill="{c}"/><circle cx="6" cy="-8" r="2.7" fill="{c}"/>'
            f'<ellipse cx="5.8" cy="-13" rx=".9" ry="3.4" fill="{c}" transform="rotate(-12 5.8 -13)"/>'
            f'<ellipse cx="7.4" cy="-12.6" rx=".9" ry="3.2" fill="{c}" transform="rotate(14 7.4 -12.6)"/>'
            '<circle cx="-6" cy="-5" r="1.6" fill="#f4f6f8"/><circle cx="7.2" cy="-8.4" r=".45" fill="#1a1410"/>')
    return move(ctx, -40, 324, 1240, 324, 46, -46 * .42, f'<g transform="scale(1.15)"><g class="fx-hop">{body}</g></g>')


def easter_fires(ctx):
    if ctx.tod == 'day':
        return ''
    u = ctx.uniform
    s = ('<defs><radialGradient id="fx-fireglow"><stop offset="0" stop-color="#ffb347" stop-opacity=".75"/>'
         '<stop offset=".5" stop-color="#ff7a2f" stop-opacity=".3"/><stop offset="1" stop-color="#ff7a2f" stop-opacity="0"/></radialGradient></defs>')
    for x in (OX + 112, OX + 262, OX + 372, 140, 1050):
        s += (f'<ellipse cx="{x}" cy="{BASE + 10}" rx="34" ry="9" fill="url(#fx-fireglow)" class="fx-pulse"/>'
              f'<ellipse cx="{x}" cy="318" rx="38" ry="22" fill="url(#fx-fireglow)"/>')
        for _ in range(4):
            dx, h, w = u(-6, 6), u(12, 20), u(4, 7)
            s += (f'<path class="fx-flicker" style="--fd:{num(u(.25, .5))}s" d="M{num(x + dx - w)} 324 Q{num(x + dx - w * .6)} {num(324 - h * .6)} '
                  f'{num(x + dx)} {num(324 - h)} Q{num(x + dx + w * .6)} {num(324 - h * .6)} {num(x + dx + w)} 324 Z" '
                  f'fill="{ctx.pick(["#ffb347", "#ff7a2f", "#ffd36e"])}" opacity=".92"/>')
        s += f'<path d="M{x - 9} 324 L{x + 9} 320 M{x - 8} 320 L{x + 8} 324" stroke="#3a2418" stroke-width="1.6"/>'
        if ctx.animated:
            for _ in range(9):
                d = u(1.6, 3)
                s += (f'<circle cx="{num(x + u(-5, 5))}" cy="318" r=".9" fill="#ffd36e" class="fx-spark" '
                      f'style="--d:{num(d)}s;--dl:-{num(u(0, d))}s;--dx:{num(ctx.dir * u(8, 30))}px"/>')
    return s


def shooting_stars(ctx):
    if not ctx.night or not ctx.animated:
        return ''
    u = ctx.uniform
    s = []
    for _ in range(7):
        x, y, side, d = u(250, 1050), u(10, 150), 1 if ctx.rng.random() < .5 else -1, u(5, 11)
        s.append(f'<g transform="translate({num(x)} {num(y)}) scale({side} 1)"><g class="fx-meteor" style="--d:{num(d)}s;--dl:-{num(u(0, d))}s">'
                 '<path d="M0 0 L-70 -24" stroke="#fff" stroke-width=".6" opacity=".35" stroke-linecap="round"/>'
                 '<path d="M0 0 L-38 -13" stroke="#fff" stroke-width="1.3" stroke-linecap="round"/></g></g>')
    return ''.join(s)


def blue_port(ctx):
    """Blue Port: the harbour lit in blue."""
    o = OX
    u = ctx.uniform
    s = ('<defs><radialGradient id="fx-blue"><stop offset="0" stop-color="#3d8bff" stop-opacity=".85"/>'
         '<stop offset=".55" stop-color="#2a6dff" stop-opacity=".3"/><stop offset="1" stop-color="#2a6dff" stop-opacity="0"/></radialGradient></defs>'
         f'<g style="mix-blend-mode:screen" opacity="{.4 if ctx.tod == "day" else 1}">')
    for cx, cy, rx, ry in ((o + 123, 290, 72, 46), (o + 221, 276, 30, 70), (o + 282, 250, 16, 95), (o + 350, 300, 60, 40),
                           (o + 440, 300, 60, 40), (o + 530, 300, 60, 40), (o + 620, 300, 60, 40), (o - 60, 295, 90, 40),
                           (o - 200, 295, 90, 40), (o - 330, 295, 80, 40)):
        s += f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#fx-blue)"/>'
    s += f'<rect y="{BASE}" width="{W}" height="{H - BASE}" fill="#1e6dff" opacity=".16"/>'
    for _ in range(40):
        x, y, w, fd = u(0, 1200), u(BASE + 6, BASE + 180), u(12, 40), u(3, 6)
        s += (f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="1.6" rx=".8" fill="#5aa8ff" class="fx-twinkle" '
              f'style="--fd:{num(fd)}s;--dl:-{num(u(0, fd))}s"/>')
    return s + '</g>'


def pumpkins(ctx):
    s = []
    for x in (OX + 20, OX + 96, OX + 188, OX + 300, OX + 360, 120, 980, 1110):
        g = ctx.uniform(.9, 1.25)
        s.append(f'<g transform="translate({num(x)} 324) scale({num(g)})"><circle cy="-5" r="11" fill="#ff9a3c" opacity=".28"/>'
                 f'<ellipse cy="-4.5" rx="6.2" ry="4.6" fill="{"#ff8a1f" if ctx.tod == "day" else "#d8701a"}"/>'
                 '<path d="M-2.2 -8.6 V-4 M2.2 -8.6 V-4" stroke="#b85a10" stroke-width=".6"/>'
                 '<path d="M0 -9 q1 -2 2.4 -2.4" stroke="#4a6a2a" stroke-width="1.1" fill="none"/>'
                 f'<g fill="#ffe08a" class="fx-glimmer" style="--fd:{num(ctx.uniform(.15, .35))}s"><path d="M-3.4 -5.6 L-1.6 -5.6 L-2.5 -7 Z M1.6 -5.6 L3.4 -5.6 L2.5 -7 Z"/>'
                 '<path d="M-3.4 -3.4 Q0 -.6 3.4 -3.4 L2 -2.8 L1.2 -2.2 L0 -2.8 L-1.2 -2.2 L-2 -2.8 Z"/></g></g>')
    return ''.join(s)


def bats(ctx):
    if ctx.tod == 'day':
        return ''
    u = ctx.uniform
    shape = 'M0 0 C-2 -2 -4 -3 -7 -2 C-6 0 -8 1 -9 3 C-6 2 -4 2 -2 3 L0 1 L2 3 C4 2 6 2 9 3 C8 1 6 0 7 -2 C4 -3 2 -2 0 0 Z'
    s = []
    for _ in range(12):
        y = u(30, 260)
        side = 1 if ctx.rng.random() < .5 else -1
        x0 = u(-200, 600) if side > 0 else u(600, 1400)
        d = u(10, 18)
        inner = (f'<g class="fx-bob" style="--ba:{num(u(4, 10))}px;--bd:{num(u(.6, 1.2))}s"><path class="fx-flap" style="--fd:{num(u(.12, .2))}s" '
                 f'd="{shape}" fill="#0e0b14" stroke="#7a6a9a" stroke-width=".5"/></g>')
        s.append(move(ctx, x0, y, x0 + side * u(300, 700), y + u(-60, 60), d, -u(0, d), inner, True))
    return ''.join(s)


def lanterns(ctx):
    """St. Martin's lantern procession along the quay, mirrored in the water."""
    if ctx.tod == 'day':
        return ''
    u = ctx.uniform
    colors = ['#ffb347', '#ff6f61', '#ffd36e', '#9be7ff', '#c3a6ff', '#8affc1']
    s = []
    for i in range(18):
        c = ctx.pick(colors)
        inner = (f'<g class="fx-bob" style="--ba:{num(u(.8, 1.8))}px;--bd:{num(u(.5, .9))}s"><path d="M0 0 V-9" stroke="#2c2f3a" stroke-width=".6"/>'
                 f'<circle cy="-11.5" r="5.5" fill="{c}" opacity=".22"/><rect x="-2.6" y="-14" width="5.2" height="5" rx="2.2" fill="{c}" filter="url(#fx-glow)"/>'
                 '<path d="M-2.2 -14.2 H2.2 M-2.2 -8.8 H2.2" stroke="#3a3020" stroke-width=".6"/></g>')
        s.append(move(ctx, -300 - i * 16, 322, 1500 - i * 16, 322, 120, -68, inner))
    s = ''.join(s)
    return s + f'<g transform="matrix(1 0 0 -1 0 {2 * BASE})" opacity=".25">{s}</g>'


def gold_stars(ctx):
    u = ctx.uniform
    s = []
    for _ in range(14):
        x, y, g, fd = u(300, 900), u(20, 200), u(.6, 1.2), u(1.2, 2.8)
        s.append(f'<g transform="translate({num(x)} {num(y)}) scale({num(g)})"><path d="M0 -6 L1.4 -1.4 L6 0 L1.4 1.4 L0 6 L-1.4 1.4 L-6 0 L-1.4 -1.4 Z" '
                 f'fill="#ffe7a0" class="fx-twinkle" style="--fd:{num(fd)}s;--dl:-{num(u(0, fd))}s"/></g>')
    return ''.join(s)


def sleigh(ctx):
    if not ctx.night:
        return ''
    c = '#f2d48a'
    s = ''
    for i in range(3):
        x = 24 + i * 16
        s += (f'<g transform="translate({x} 0)"><ellipse rx="5" ry="2.2" fill="{c}"/><path d="M4 -1 L7 -4 M-3 1.5 L-5 5 M-1 1.5 L-1 5 '
              f'M2 1.5 L3 5 M3.5 1.5 L5 5 M6.5 -4 L7.5 -7 M6.5 -4 L9 -6" stroke="{c}" stroke-width=".8" stroke-linecap="round"/>'
              f'<circle cx="7.5" cy="-4" r="1.3" fill="{c}"/></g>')
    s += ('<circle cx="65" cy="-3.6" r="1.4" fill="#ff4a3a" filter="url(#fx-glow)"/>'
          f'<path d="M-14 -2 L-12 -8 H0 L3 -2 Z" fill="{c}"/><path d="M-16 -.5 H4 Q9 -.5 9 -5" stroke="{c}" stroke-width=".9" fill="none"/>'
          f'<path d="M3 -6 L20 -1" stroke="{c}" stroke-width=".4"/>')
    for i in range(5):
        s += f'<circle cx="{-22 - i * 8}" cy="{-1 if i % 2 else -4}" r="{num(1 - i * .15)}" fill="{c}" opacity="{num(.8 - i * .14)}"/>'
    return move(ctx, -300, 72, 3000, 52, 40, -40 * .27, f'<g transform="scale(1.2)">{s}</g>')


def first_snow(ctx):
    """Big flakes and a snowman on the quay."""
    u = ctx.uniform
    c = '#c9d3e3' if ctx.night else '#f4f8fc'
    s = []
    for _ in range(40):
        x0, d = u(-50, 1250), u(16, 26)
        inner = f'<g class="fx-sway" style="--sw:{num(u(10, 24))}px;--sd:{num(u(2.5, 4))}s"><circle r="{num(u(2, 3.6))}" fill="{c}" opacity=".9"/></g>'
        s.append(move(ctx, x0, -20, x0 + ctx.dir * u(10, 60), u(860, 900), d, -u(0, d), inner))
    return ''.join(s) + (
        f'<g transform="translate({OX + 262} 324)"><circle cy="-5" r="5" fill="{c}"/><circle cy="-13" r="3.8" fill="{c}"/><circle cy="-19.4" r="2.8" fill="{c}"/>'
        '<path d="M-2.4 -21.6 H2.4 M-1.6 -21.6 V-25 H1.6 V-21.6 Z" stroke="#1b1f27" stroke-width="1.2" fill="#1b1f27"/>'
        '<path d="M.6 -19.4 L4 -18.8 L.6 -18.4 Z" fill="#ff8a1f"/><circle cx="-1" cy="-20.2" r=".4" fill="#1b1f27"/><circle cx="1" cy="-20.2" r=".4" fill="#1b1f27"/>'
        '<path d="M-3.4 -16.4 Q0 -15 3.4 -16.4 L3.6 -15 L2.6 -12" stroke="#e0322f" stroke-width="1.3" fill="none" stroke-linecap="round"/>'
        '<path d="M-3.6 -13 L-8 -16 M3.6 -13 L8 -15.4" stroke="#5a4030" stroke-width=".7"/></g>')


def hot_air_balloons(ctx):
    u = ctx.uniform
    colors = [('#ff5a4f', '#ffd262'), ('#4fa3ff', '#ffffff'), ('#5fd38d', '#ffd262')]
    s = []
    for i in range(3):
        y, x0, d, g = u(60, 200), OX + 40 + i * 120, u(160, 240), u(1, 1.6)
        a, b = colors[i]
        h = (f'<path d="M0 -22 C12 -22 14 -8 6 2 L3 6 H-3 L-6 2 C-14 -8 -12 -22 0 -22 Z" fill="{a}"/>'
             f'<path d="M0 -22 C5 -22 6 -8 2.6 2 L1.5 6 H-1.5 L-2.6 2 C-6 -8 -5 -22 0 -22 Z" fill="{b}"/>'
             '<path d="M-3 6 L-2 10 M3 6 L2 10" stroke="#3a3020" stroke-width=".5"/><rect x="-2.4" y="10" width="4.8" height="3.2" fill="#6b4a2a"/>')
        if ctx.tod != 'day':
            h += '<path d="M0 9 Q-1.4 6.6 0 4.6 Q1.4 6.6 0 9 Z" fill="#ffb347" class="fx-glimmer" style="--fd:.3s"/>'
        inner = f'<g class="fx-bob" style="--ba:3px;--bd:4s"><g transform="scale({num(g)})">{h}</g></g>'
        s.append(move(ctx, x0, y, x0 + ctx.dir * u(500, 900), y - u(20, 60), d, -u(0, d * .3), inner))
    return ''.join(s)


def kites(ctx):
    if ctx.night:
        return ''
    u = ctx.uniform
    height = {'calm': 250, 'windy': 150, 'storm': 110}[ctx.wind]
    sd = .6 if ctx.wind == 'storm' else 1.4 if ctx.wind == 'windy' else 3
    colors = [('#ff5a4f', '#ffd262'), ('#4fa3ff', '#ffffff'), ('#c58bff', '#5fd38d')]
    s = []
    for i in range(3):
        ax, ay = OX + 80 + i * 110, 322
        kx, ky = ax + ctx.dir * u(60, 120), height + u(-30, 30)
        a, b = colors[i]
        s.append(f'<path d="M{ax} {ay} Q{num((ax + kx) / 2)} {num((ay + ky) / 2 + 30)} {num(kx)} {num(ky + 8)}" stroke="#e8eef5" stroke-width=".4" fill="none" opacity=".6"/>'
                 f'<g transform="translate({num(kx)} {num(ky)})"><g class="fx-sway" style="--sw:{3 if ctx.wind == "calm" else 6}px;--sd:{sd}s">'
                 f'<path d="M0 -10 L7 0 L0 8 L-7 0 Z" fill="{a}"/><path d="M0 -10 L7 0 L0 0 Z M0 8 L-7 0 L0 0 Z" fill="{b}"/>'
                 f'<path d="M0 8 q-4 6 0 10 q4 4 0 10 q-4 4 0 9" stroke="{a}" stroke-width=".8" fill="none"/></g></g>')
    return ''.join(s)


def garbage_truck(ctx):
    if ctx.night:
        return ''
    truck = ('<rect x="-14" y="-10" width="18" height="9" rx="1" fill="#ff7a1a"/><path d="M4 -8 H9 L12 -4.5 V-1 H4 Z" fill="#ff7a1a"/>'
             '<path d="M5 -7.2 H8.4 L10.4 -4.6 H5 Z" fill="#9fc3e0"/><circle cx="-9" cy="-.6" r="2" fill="#1b1f27"/>'
             '<circle cx="-3" cy="-.6" r="2" fill="#1b1f27"/><circle cx="8" cy="-.6" r="2" fill="#1b1f27"/>'
             '<rect x="5" y="-9.6" width="3" height="1.4" rx=".5" fill="#ffb300" class="fx-lamp"/><path d="M-13 -5.5 H3" stroke="#ffffff" stroke-width=".8" opacity=".8"/>')
    return move(ctx, -60, 324, 1260, 324, 70, -70 * .42, f'<g transform="scale(1.1)">{truck}</g>')


def tulips(ctx):
    u = ctx.uniform
    s = []
    for _ in range(34):
        x, h = u(0, 1200), u(6, 10)
        c = ctx.pick(['#ff5a6e', '#ffd262', '#ff8fb1', '#c58bff', '#ff7a2f', '#ffffff'])
        s.append(f'<g transform="translate({num(x)} 324)"><g class="fx-sway" style="--sw:{num(u(.4, 1))}px;--sd:{num(u(1.5, 3))}s">'
                 f'<path d="M0 0 V-{num(h)}" stroke="#3f8a4a" stroke-width=".8"/>'
                 f'<path d="M-1.8 -{num(h)} L-1.8 -{num(h + 3)} L-.6 -{num(h + 2)} L0 -{num(h + 3.4)} L.6 -{num(h + 2)} L1.8 -{num(h + 3)} L1.8 -{num(h)} '
                 f'Q0 -{num(h - 1.2)} -1.8 -{num(h)} Z" fill="{c}"/></g></g>')
    return ''.join(s)


def epiphany_star(ctx):
    inner = ('<path d="M0 0 L120 -18" stroke="#fff1c4" stroke-width="1.6" opacity=".25" stroke-linecap="round"/>'
             '<path d="M0 0 L60 -9" stroke="#fff6dc" stroke-width="1" opacity=".5"/><circle r="9" fill="#ffe7a0" opacity=".3"/>'
             '<path d="M0 -6 L1.4 -1.4 L6 0 L1.4 1.4 L0 6 L-1.4 1.4 L-6 0 L-1.4 -1.4 Z" fill="#fff6dc" class="fx-twinkle" style="--fd:1.6s;--dl:0s"/>')
    return move(ctx, 1100, 60, 300, 90, 90, -40, inner)


def smoke(ctx):
    """New Year's morning: the last of the fireworks smoke."""
    u = ctx.uniform
    c = '#4a4f5e' if ctx.night else '#c9cdd4'
    s = '<defs><filter id="fx-soft3" x="-30%" y="-80%" width="160%" height="260%"><feGaussianBlur stdDeviation="14"/></filter></defs>'
    for _ in range(9):
        y, w, h, x0, d = u(120, 330), u(160, 360), u(20, 44), u(-200, 1200), u(50, 90)
        inner = f'<ellipse rx="{num(w / 2)}" ry="{num(h / 2)}" fill="{c}" opacity=".38" filter="url(#fx-soft3)"/>'
        s += move(ctx, x0, y, x0 + ctx.dir * u(150, 300), y - 20, d, -u(0, d), inner, True)
    return s


# --- Special days inside the scene (coordinates of the skyline group) ------------
def crane_lights(ctx, colors):
    s = []
    for x in CRANES:
        for lx in range(x - 10, x + 55, 5):
            fd = ctx.uniform(1.2, 2.6)
            s.append(f'<circle cx="{lx}" cy="133" r=".95" fill="{ctx.pick(colors)}" class="fx-twinkle" '
                     f'style="--fd:{num(fd)}s;--dl:-{num(ctx.uniform(0, fd))}s"/>')
    return ''.join(s)


def advent_lights(ctx):
    o = OX
    s = crane_lights(ctx, ['#ffd27a'])
    for lx in range(o + 72, o + 175, 4):
        yy, fd = 131 + math.sin((lx - o) / 6) * 1.2, ctx.uniform(1, 2.4)
        s += (f'<circle cx="{lx}" cy="{num(yy)}" r=".8" fill="{ctx.pick(["#ffd27a", "#ff7a6a", "#fff3d0"])}" class="fx-twinkle" '
              f'style="--fd:{num(fd)}s;--dl:-{num(ctx.uniform(0, fd))}s"/>')
    s += (f'<circle cx="{o + 221}" cy="21" r="10" fill="#ffe7a0" opacity=".25"/>'
          f'<path d="M{o + 221} 14 L{o + 222.6} 19.4 L{o + 228} 21 L{o + 222.6} 22.6 L{o + 221} 28 L{o + 219.4} 22.6 L{o + 214} 21 '
          f'L{o + 219.4} 19.4 Z" fill="#fff1c4" class="fx-twinkle" style="--fd:3s;--dl:0s"/>')
    return s


def snow_caps(ctx):
    o, c = OX, '#d6deec' if ctx.night else '#f6f9fc'
    d = ''
    for x in range(o - 350, o + 66, 70):
        d += (f'M{x} 150 L{x + 6} 142 L{x + 12} 150 M{x + 12} 146 L{x + 18} 138 L{x + 24} 146 '
              f'M{x + 28} 144 L{x + 34} 136 L{x + 40} 144 M{x + 46} 140 L{x + 53} 131 L{x + 60} 140 ')
    d += (f'M{o + 70} 96 Q{o + 80} 80 {o + 92} 92 Q{o + 104} 70 {o + 120} 88 Q{o + 132} 72 {o + 146} 88 Q{o + 158} 78 {o + 168} 94 '
          f'Q{o + 172} 90 {o + 176} 96 ')
    d += (f'M{o + 196} 150 H{o + 212} M{o + 230} 150 H{o + 250} M{o + 209} 86 H{o + 233} M{o + 214} 70 H{o + 228} '
          f'M{o + 215} 70 Q{o + 221} 57 {o + 227} 70 M{o + 274} 60 H{o + 290} M{o + 276} 71 H{o + 288} M{o + 292} 172 H{W} M0 184 H{W} ')
    for x in CRANES:
        d += f'M{x - 12} 134 H{x + 56} M{x} 146 H{x + 40} '
    return (f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" '
            'transform="translate(0 -0.9)"/>')


def bunting(ctx):
    colors = ['#ff5a4f', '#ffd262', '#4fa3ff', '#ffffff', '#5fd38d']
    s = ''
    for a0, b0 in zip(CRANES, CRANES[1:]):
        a, b, y, cy = a0 + 22, b0 + 22, 113, 124
        m = (a + b) / 2
        s += f'<path d="M{a} {y} Q{num(m)} {cy} {b} {y}" stroke="#cfd6de" stroke-width=".5" fill="none" opacity=".8"/>'
        for i in range(1, 10):
            t = i / 10
            px = (1 - t) ** 2 * a + 2 * (1 - t) * t * m + t * t * b
            py = (1 - t) ** 2 * y + 2 * (1 - t) * t * cy + t * t * y
            s += f'<path d="M{num(px - 1.6)} {num(py)} H{num(px + 1.6)} L{num(px)} {num(py + 3.4)} Z" fill="{colors[i % len(colors)]}"/>'
    return s


def easter_eggs(ctx):
    s = ''
    for x in CRANES:
        for lx in range(x - 8, x + 53, 9):
            s += (f'<path d="M{lx} 138 V141" stroke="#d9dee4" stroke-width=".4"/>'
                  f'<ellipse cx="{lx}" cy="143" rx="1.4" ry="1.9" fill="{ctx.pick(["#ffb3c7", "#b3e5ff", "#fff2a8", "#c8f7c5", "#e0c3ff"])}"/>')
    return s


def ferris_wheel(ctx):
    """The Hamburger Dom's Ferris wheel."""
    cx, cy, rad = OX + 255, 116, 19
    dark = ctx.tod != 'day'
    st = '#3a4560' if dark else '#c7d0da'
    spokes = ''.join(f'M0 0 L{num(math.cos(i / 10 * 2 * math.pi) * rad)} {num(math.sin(i / 10 * 2 * math.pi) * rad)} ' for i in range(10))
    lights = ''
    for i in range(20):
        a, fd = i / 20 * 2 * math.pi, ctx.uniform(.8, 1.8)
        extra = f' class="fx-twinkle" style="--fd:{num(fd)}s;--dl:-{num(ctx.uniform(0, fd))}s"' if dark else ' opacity=".5"'
        lights += (f'<circle cx="{num(math.cos(a) * rad)}" cy="{num(math.sin(a) * rad)}" r="{1.1 if dark else .8}" '
                   f'fill="{("#ffd27a", "#ff6f9a", "#7fd8ff")[i % 3]}"{extra}/>')
    s = f'<ellipse cx="{cx}" cy="150" rx="46" ry="16" fill="#ff9a6a" opacity=".28"/>' if dark else ''
    s += f'<path d="M{cx - 10} 152 L{cx} {cy} L{cx + 10} 152" stroke="{st}" stroke-width="1.2" fill="none"/>'
    return (s + f'<g transform="translate({cx} {cy})"><g class="fx-turn"><circle r="{rad}" fill="none" stroke="{st}" stroke-width="1"/>'
            f'<path d="{spokes}" stroke="{st}" stroke-width=".5"/>{lights}</g></g>')


def santa_hats():
    def hat(x, y, g):
        return (f'<g transform="translate({x} {y}) scale({g})"><path d="M-5 0 Q-4 -7 1 -10 Q5 -11 6 -7 Q3 -8 2 -6 Q4 -3 5 0 Z" fill="#e0322f"/>'
                '<rect x="-5.6" y="-1" width="11.2" height="2.6" rx="1.2" fill="#f4f6f8"/><circle cx="6" cy="-7" r="1.6" fill="#f4f6f8"/></g>')
    return hat(OX + 221, 31, .9) + hat(OX + 282, 13, .8)


def christmas_tree(ctx):
    x, b = OX + 186, 184
    g = '#2a6a46' if ctx.tod == 'day' else '#183f2c'
    s = (f'<path d="M{x - 1} {b} V{b - 4} H{x + 1} V{b} Z" fill="#4a3020"/>'
         f'<path d="M{x - 10} {b - 4} L{x} {b - 16} L{x + 10} {b - 4} Z M{x - 8} {b - 12} L{x} {b - 24} L{x + 8} {b - 12} Z '
         f'M{x - 6} {b - 19} L{x} {b - 31} L{x + 6} {b - 19} Z" fill="{g}"/>')
    for _ in range(16):
        yy = ctx.uniform(b - 28, b - 6)
        w, fd = (yy - (b - 31)) / 27 * 8, ctx.uniform(.8, 2)
        s += (f'<circle cx="{num(x + ctx.uniform(-w, w))}" cy="{num(yy)}" r=".8" fill="{ctx.pick(["#ffd27a", "#ff6f6f", "#9fe3ff", "#fff3d0"])}" '
              f'class="fx-twinkle" style="--fd:{num(fd)}s;--dl:-{num(ctx.uniform(0, fd))}s"/>')
    return s + (f'<path d="M{x} {b - 35} L{x + 1.2} {b - 32} L{x + 4} {b - 31.5} L{x + 1.6} {b - 30} L{x + 2.4} {b - 27} L{x} {b - 28.6} '
                f'L{x - 2.4} {b - 27} L{x - 1.6} {b - 30} L{x - 4} {b - 31.5} L{x - 1.2} {b - 32} Z" fill="#fff1c4"/>')


def rainbow_flags(ctx):
    colors = ['#e40303', '#ff8c00', '#ffed00', '#008026', '#004dff', '#750787']
    s = ''
    for x in CRANES:
        stripes = ''.join(f'<rect x="0" y="{num(i * 1.1)}" width="9" height="1.1" fill="{c}"/>' for i, c in enumerate(colors))
        s += (f'<path d="M{x + 22} 112 V102" stroke="#cfd6de" stroke-width=".5"/><g transform="translate({x + 22} 102) scale({ctx.dir} 1)">'
              f'<g class="fx-flutter" style="--fa:5deg;--fd:.7s">{stripes}</g></g>')
    return s


def michel_clock(forward):
    """The Michel's clock face, hands racing forward (spring) or back (autumn) when the clocks change."""
    cx, cy = OX + 221, 101
    sense = 'normal' if forward else 'reverse'
    return (f'<circle cx="{cx}" cy="{cy}" r="7" fill="#fff1c4" opacity=".3" class="fx-pulse"/><circle cx="{cx}" cy="{cy}" r="3.6" fill="#fff6dc"/>'
            f'<g transform="translate({cx} {cy})"><g class="fx-turn" style="animation-duration:36s;animation-direction:{sense}">'
            '<path d="M0 0 V-2.2" stroke="#2a2a2a" stroke-width=".7" stroke-linecap="round"/></g>'
            f'<g class="fx-turn" style="animation-duration:3s;animation-direction:{sense}">'
            '<path d="M0 0 V-3" stroke="#2a2a2a" stroke-width=".45" stroke-linecap="round"/></g></g>')


def solstice(ctx):
    """Returns (defs, fragment behind the city)."""
    if ctx.night:
        defs = ('<linearGradient id="fx-white-night" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7fb6d6" stop-opacity="0"/>'
                '<stop offset=".6" stop-color="#7fb6d6" stop-opacity=".28"/><stop offset="1" stop-color="#b9d9c8" stop-opacity=".5"/></linearGradient>')
        return defs, f'<rect y="110" width="{W}" height="{BASE - 110}" fill="url(#fx-white-night)"/>'
    day = ctx.tod == 'day'
    cx, cy = (OX + 317, 99) if day else (OX + 212, 312)
    rays = ''
    for i in range(14):
        a = i / 14 * math.pi * 2 if day else math.pi + (i + .5) / 14 * math.pi
        b = .07
        rays += (f'<path d="M0 0 L{num(math.cos(a - b) * 900)} {num(math.sin(a - b) * 900)} '
                 f'L{num(math.cos(a + b) * 900)} {num(math.sin(a + b) * 900)} Z"/>')
    cls = 'class="fx-turn" style="animation-duration:240s"' if day else 'class="fx-pulse"'
    return '', (f'<g transform="translate({cx} {cy})" fill="{"#fff3c4" if day else "#ffc27a"}" opacity="{.12 if day else .2}">'
                f'<g {cls}>{rays}</g></g>')


def floodlight(ctx, club):
    """A home match: the stadium lights glow over the roofs -- the Millerntor just behind the Elbphilharmonie and
    the Michel, the Volksparkstadion smaller and fainter, far off in the west. Returns (defs, fragment behind the
    city); without club colours, the light is the same for both."""
    x, size = (OX + 186, 1) if club == 'match-st-pauli' else (OX + 26, .7)
    strength = {'day': .35, 'dusk': .8, 'night': 1}[ctx.tod] * (1 if size == 1 else .75)
    y = 260  # just above the roofs
    defs = ('<radialGradient id="fx-flood"><stop offset="0" stop-color="#f6f9ff" stop-opacity=".95"/>'
            '<stop offset=".4" stop-color="#e4edff" stop-opacity=".45"/><stop offset="1" stop-color="#d2e1ff" stop-opacity="0"/>'
            '</radialGradient>')
    beams = ''.join(f'<path d="M-2 0 L2 0 L{num(12 * size)} {num(-140 * size)} L{num(-12 * size)} {num(-140 * size)} Z" '
                    f'transform="translate({num(x + (i - 2.5) * 15 * size)} {y}) rotate({num((i - 2.5) * 6)})"/>'
                    for i in range(6)) if ctx.tod != 'day' else ''
    lamps = ''.join(f'<rect x="{num(x + dx * size)}" y="{num(y - 7 * size)}" width="{num(13 * size)}" height="{num(2.6 * size)}" rx="1"/>'
                    for dx in (-48, -24, 10, 34))
    pulse = ' class="fx-pulse"' if ctx.animated else ''
    return defs, (f'<g opacity="{num(strength)}"><ellipse cx="{x}" cy="{y}" rx="{num(130 * size)}" ry="{num(85 * size)}" '
                  f'fill="url(#fx-flood)"{pulse}/><g fill="#eef4ff" opacity=".08">{beams}</g>'
                  f'<g fill="#ffffff" filter="url(#fx-glow)">{lamps}</g></g>')


# --- Composition ------------------------------------------------------------------
GLOW_DEFS = ('<filter id="fx-glow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="1.4" result="b"/>'
             '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
             '<filter id="fx-glow2" x="-50%" y="-10%" width="200%" height="120%"><feGaussianBlur stdDeviation="2.5" result="b"/>'
             '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
             '<linearGradient id="fx-haze" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffd59a" stop-opacity="0"/>'
             '<stop offset=".26" stop-color="#ffcf8a" stop-opacity=".16"/><stop offset=".39" stop-color="#ffb867" stop-opacity=".34"/>'
             '<stop offset=".52" stop-color="#ffd59a" stop-opacity=".1"/><stop offset="1" stop-color="#ffd59a" stop-opacity="0"/></linearGradient>'
             '<radialGradient id="fx-heat-sun"><stop offset="0" stop-color="#fff1c2" stop-opacity=".7"/>'
             '<stop offset=".45" stop-color="#ffd27a" stop-opacity=".28"/><stop offset="1" stop-color="#ffb04a" stop-opacity="0"/></radialGradient>')
HEAT_SHIMMER = ('<filter id="fx-heat" x="-2%" y="-10%" width="104%" height="120%"><feTurbulence type="fractalNoise" baseFrequency="0.012 0.09" '
                'numOctaves="1" seed="3" result="noise"><animate attributeName="baseFrequency" dur="5s" values="0.012 0.09;0.015 0.11;0.012 0.09" '
                'repeatCount="indefinite"/></feTurbulence><feDisplacementMap in="SourceGraphic" in2="noise" scale="5" xChannelSelector="R" '
                'yChannelSelector="G"/></filter>')
# Days that bring their own pictures. A quiet day (Good Friday, Remembrance Sunday,
# Sunday of the Dead) is not in here and so gets none.
PLAYFUL_DAYS = {'valentines', 'easter', 'cherry-blossom', 'harbour-birthday', 'ascension', 'mothers-day', 'solstice', 'pride', 'dom', 'shooting-stars',
                'blue-port', 'school-holidays', 'halloween', 'st-martin', 'first-snow', 'advent', 'st-nicholas', 'christmas', 'new-years-eve', 'new-years-day',
                'epiphany', 'carnival', 'clock-change', 'birthday', 'bin-day', 'match-st-pauli', 'match-hsv'}


def layers(ctx, palette):
    """All fragments for scene.compose(). palette: the entry from PALETTES."""
    near, water = palette['near'], palette['water'][0][1]
    f = ctx.day if ctx.day in PLAYFUL_DAYS else 'none'
    tod, night, ex = ctx.tod, ctx.night, ctx.extremes
    defs = GLOW_DEFS
    behind, back, front, glass, ferry, over = '', '', '', '', '', ''
    # inside the city
    if 'snow-cover' in ex:
        front += snow_caps(ctx)
    if f in ('advent', 'st-nicholas', 'christmas', 'epiphany'):
        front += advent_lights(ctx)
    if f == 'st-nicholas':
        front += santa_hats()
    if f in ('christmas', 'epiphany'):
        front += christmas_tree(ctx)
    if f in ('harbour-birthday', 'birthday'):
        front += bunting(ctx)
    if f == 'easter':
        front += easter_eggs(ctx)
    if f == 'clock-change':
        front += michel_clock(ctx.season == 'spring')
    if f == 'blue-port':
        front += crane_lights(ctx, ['#4fb0ff', '#7fc8ff'])
    if f == 'pride':
        front += rainbow_flags(ctx)
        defs += ('<linearGradient id="fx-rainbow" gradientUnits="userSpaceOnUse" x1="' + str(OX + 70) + '" y1="0" x2="' + str(OX + 176) + '" y2="0">'
                 + ''.join(f'<stop offset="{num(i / 5)}" stop-color="{c}"/>' for i, c in
                           enumerate(['#e40303', '#ff8c00', '#ffed00', '#008026', '#004dff', '#750787'])) + '</linearGradient>')
    glass_tint = {'valentines': ('#ff7aa8', .25 if tod == 'day' else .42), 'blue-port': ('#3a8bff', .25 if tod == 'day' else .45),
                  'pride': ('url(#fx-rainbow)', .5 if tod == 'day' else .65)}.get(f)
    if glass_tint:
        o = OX
        glass = (f'<g opacity="{glass_tint[1]}"><path d="M{o+70} 128 V96 Q{o+80} 80 {o+92} 92 Q{o+104} 70 {o+120} 88 Q{o+132} 72 {o+146} 88 '
                 f'Q{o+158} 78 {o+168} 94 Q{o+172} 90 {o+176} 96 V128 Z" fill="{glass_tint[0]}" class="fx-pulse"/></g>')
    if f == 'dom':
        back += ferris_wheel(ctx)
    if f == 'solstice':
        d2, behind = solstice(ctx)
        defs += d2
    if f in ('match-st-pauli', 'match-hsv'):
        d2, behind = floodlight(ctx, f)
        defs += d2
    if 'heat' in ex:
        defs += HEAT_SHIMMER
    # on the ferry
    if 'cold' in ex and ctx.animated:
        ferry += ''.join(f'<circle cx="35.5" cy="1" r="2.2" fill="#eef3f8" class="fx-steam" style="--dl:-{num(i * .85)}s;--dx:{ctx.dir * 12}px"/>'
                         for i in range(4))
    if f in ('advent', 'st-nicholas', 'christmas', 'epiphany'):
        x = 4.0
        while x <= 42:
            ferry += f'<circle cx="{num(x)}" cy="{num(3.6 + math.sin(x / 4) * .6)}" r=".7" fill="{ctx.pick(["#ffd27a", "#ff7a6a", "#fff3d0"])}"/>'
            x += 3.2
    # over the scene
    if 'heat' in ex:
        over += f'<rect width="{W}" height="{H}" fill="url(#fx-haze)" opacity="{.45 if night else 1}"/>'
        if tod == 'day' and ctx.weather == 'clear':
            over += f'<circle cx="{OX + 317}" cy="99" r="210" fill="url(#fx-heat-sun)" class="fx-pulse"/>'
    if 'storm-surge' in ex:
        over += storm_surge(ctx, water)
    if 'cruise' in ctx.ships:
        over += cruise_ship(ctx)
    if 'container' in ctx.ships:
        over += container_ship(ctx)
    if 'ice-drift' in ex:
        over += pack_ice(ctx)
    elif 'cold' in ex:
        over += ice_floes(ctx)
    if (ctx.wind != 'calm' or 'storm-surge' in ex) and 'ice-drift' not in ex:  # pack ice keeps the waves down
        over += whitecaps(ctx, 60 if ctx.wind == 'storm' or 'storm-surge' in ex else 30)
    if ctx.season == 'summer' and not night:
        over += sailboats(ctx, near)
    if f == 'harbour-birthday':
        over += tall_ship(ctx, near)
    if f == 'halloween':
        if tod != 'day':
            over += tall_ship(ctx, near, ghost=True)
        if night and ctx.weather == 'clear':
            over += (f'<circle cx="{OX + 314}" cy="97" r="46" fill="#ff8a2a" opacity=".22"/>'
                     f'<circle cx="{OX + 314}" cy="97" r="26" fill="#ffb060" opacity=".3" style="mix-blend-mode:screen"/>')
        over += pumpkins(ctx)
    if f == 'blue-port':
        over += blue_port(ctx)
    if f == 'easter':
        over += easter_fires(ctx) + hare(ctx)
    if f == 'st-martin':
        over += lanterns(ctx)
    if f == 'bin-day':
        over += garbage_truck(ctx)
    if f == 'mothers-day':
        over += tulips(ctx)
    if f == 'first-snow':
        over += first_snow(ctx)
    if ctx.season == 'summer' and night:
        over += fireflies(ctx)
    over += signal_mast(ctx)
    if f == 'school-holidays':
        over += kites(ctx)
    if f == 'new-years-eve' and tod != 'day':
        over += fireworks(ctx)
    if f == 'cherry-blossom' and tod != 'day':
        over += fireworks(ctx, ['#ffc2d4', '#ffffff', '#ff8fb1', '#ffe4ee', '#ffd6e4'])
    if f == 'ascension':
        over += hot_air_balloons(ctx)
    if f == 'epiphany':
        over += epiphany_star(ctx)
    if f == 'new-years-day':
        over += smoke(ctx)
    if f == 'shooting-stars':
        over += shooting_stars(ctx)
    if f == 'st-nicholas':
        over += gold_stars(ctx)
    if f == 'christmas':
        over += sleigh(ctx)
    if f == 'halloween':
        over += bats(ctx)
    if f == 'valentines':
        over += hearts(ctx)
    if f == 'birthday':
        over += balloons(ctx)
    if ctx.season == 'summer':
        over += gulls(ctx)
    if ctx.season == 'spring' and ctx.wind != 'storm':
        over += migrating_birds(ctx, 1)
    if ctx.season == 'autumn' and ctx.wind != 'storm':
        over += migrating_birds(ctx, -1)
    if 'thunder' in ex:
        over += lightning(ctx)
    if 'fog' in ex:
        over += fog(ctx)
    if ctx.wind == 'storm':
        over += gust_streaks(ctx)
    if ctx.season == 'winter' and 'snow-cover' not in ex:
        over += hoarfrost(ctx)
    factor = {'calm': 1, 'windy': 1.6, 'storm': 2}[ctx.wind]
    if ctx.season == 'autumn':
        colors = (['#6b4a3a', '#5a3a32', '#6e5a3a', '#4e3a30'] if night else
                  ['#c9663a', '#a8452f', '#cf9a3a', '#8a4a2a'] if tod == 'dusk' else
                  ['#e0803a', '#c9532f', '#e8b23a', '#a65a2a', '#d4692e'])
        bright = {'day': 1, 'dusk': .8, 'night': .5}[tod]
        over += drifters(ctx, round(28 * factor), ctx.wind, colors, LEAF, (.75, 1.35), num(.95 * max(bright, .7)))
    if ctx.season == 'spring':
        colors = ['#8c7f8f', '#a69aa8'] if night else ['#ffd6e4', '#ffffff', '#f7b8cf']
        over += drifters(ctx, round(30 * factor), ctx.wind, colors, BLOSSOM, (.8, 1.25), .9, 1.25)
    if f == 'carnival':
        over += drifters(ctx, 60, 'calm', ['#ff5a4f', '#ffd262', '#4fa3ff', '#5fd38d', '#c58bff', '#ff8fb1', '#ffffff'],
                         CONFETTI, (1, 1.6), .95, .8)
    if 'cold' in ex:
        over += frost_flowers(ctx)
    return {'defs': defs, 'behind_city': behind, 'city_back': back, 'city_front': front, 'glass': glass,
            'ferry': ferry, 'rock': ctx.wind == 'storm', 'heat_shimmer': 'heat' in ex, 'overlay': over}
