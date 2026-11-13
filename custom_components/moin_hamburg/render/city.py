"""The Hamburg skyline: silhouettes, landmarks, cranes and window lights.

All coordinates are relative to the skyline group, which the scene places at
y = SKY_TOP. The landmarks sit in the phone band starting at OX.
"""
from .palette import OX, W

BASE_CSS = """
.drop{animation:fall linear infinite}
@keyframes fall{from{transform:translateY(0)}to{transform:translateY(1000px)}}
.flake{animation:snow linear infinite}
@keyframes snow{0%{transform:translate(0,0)}25%{transform:translate(10px,240px)}50%{transform:translate(-7px,480px)}75%{transform:translate(8px,720px)}100%{transform:translate(0,960px)}}
.star{animation:twinkle ease-in-out infinite}
@keyframes twinkle{0%,100%{opacity:.2}50%{opacity:1}}
.drift{animation:drift linear infinite}
@keyframes drift{from{transform:translateX(-420px)}to{transform:translateX(1320px)}}
.shimmer{animation:shimmer ease-in-out infinite}
@keyframes shimmer{0%,100%{opacity:.1;transform:translateX(0)}50%{opacity:.75;transform:translateX(6px)}}
.ship{animation:sail 260s linear infinite}
@keyframes sail{from{transform:translateX(-80px)}to{transform:translateX(1280px)}}
@media (prefers-reduced-motion: reduce){.drop,.flake,.star,.drift,.shimmer,.ship{animation:none}}
"""

# Left edges of the container cranes
CRANES = list(range(OX + 300, W - 20, 44))


def gradient(gid, stops, x2=0, y2=1):
    s = ''.join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">{s}</linearGradient>'


def far_side(rng, x0, x1):
    """Blocky background buildings between x0 and x1."""
    d = [f'M{x0} 190']
    x = x0
    while x < x1:
        w = rng.randint(10, 26)
        h = rng.randint(126, 152)
        d.append(f'V{h} H{min(x + w, x1)}')
        x += w
    d.append('V190 Z')
    return ' '.join(d)


def speicherstadt(x0, x1):
    """Gabled rows of the Speicherstadt warehouses, 66 px pattern, from x0 to x1."""
    parts = []
    x = x0
    while x < x1:
        parts.append(
            f'M{x} 190 V150 L{x+6} 142 L{x+12} 150 V146 L{x+18} 138 L{x+24} 146 V150 H{x+28} V144 '
            f'L{x+34} 136 L{x+40} 144 V150 H{x+46} V140 L{x+53} 131 L{x+60} 140 V150 H{x+66} V190 Z')
        x += 70
    return ' '.join(parts)


def crane(x):
    """Container gantry crane, left leg at x+6."""
    return (f'M{x} 146 H{x+40} V152 H{x} Z M{x+6} 152 H{x+9} V190 H{x+6} Z M{x+31} 152 H{x+34} V190 H{x+31} Z '
            f'M{x-12} 134 H{x+56} V138 H{x-12} Z M{x+20} 134 V112 H{x+24} V134 Z')


def city(p, rng):
    """The skyline group <g id="city"> for palette p."""
    o = OX
    far = (far_side(rng, 0, o) + ' ' +
           f'M{o} 190 V150 H{o+12} V138 H{o+26} V146 H{o+40} V132 H{o+52} V142 H{o+180} V128 H{o+196} V136 '
           f'H{o+244} L{o+250} 22 L{o+256} 136 H{o+262} V120 H{o+276} V134 H{o+300} V126 H{o+318} V112 '
           f'L{o+324} 100 L{o+330} 112 V140 H{o+346} V130 H{o+362} V142 H{o+376} V134 H{o+390} V190 Z ' +
           far_side(rng, o + 390, W))
    near = [
        speicherstadt(o - 350, o + 66),
        f'M{o+70} 190 V128 H{o+176} V190 Z',                     # Kaispeicher
        f'M{o+196} 190 V150 H{o+250} V190 Z',                    # Michel: nave
        f'M{o+212} 150 V92 H{o+230} V150 Z',                     # tower
        f'M{o+209} 92 V86 H{o+233} V92 Z',
        f'M{o+214} 86 V70 H{o+228} V86 Z',
        f'M{o+215} 70 Q{o+221} 57 {o+227} 70 Z',
        f'M{o+218} 60 H{o+224} V48 H{o+218} Z',
        f'M{o+219} 48 L{o+221} 26 L{o+223} 48 Z',
        f'M{o+280} 190 V40 H{o+284} V190 Z',                     # TV tower
        f'M{o+274} 60 H{o+290} V67 H{o+274} Z',
        f'M{o+276} 71 H{o+288} V74 H{o+276} Z',
        f'M{o+281.4} 40 V8 H{o+282.6} V40 Z',
        f'M{o+292} 172 H{W} V190 H{o+292} Z',                    # container stacks
        f'M0 184 H{W} V190 H0 Z',                                # quay wall
    ]
    cranes = list(range(o + 300, W - 20, 44))
    near += [crane(x) for x in cranes]
    cables = ' '.join(f'M{x+22} 112 L{x-10} 134 M{x+22} 112 L{x+54} 134' for x in cranes)
    lights = []
    for x in list(range(4, o - 10, 9)) + list(range(o + 300, W, 13)):
        if rng.random() < .45:
            lights.append(f'<rect x="{x}" y="{rng.randint(152, 176)}" width="2" height="3"/>')
    for x, y in [(78, 106), (90, 114), (104, 100), (116, 114), (128, 98), (140, 108), (152, 116), (162, 106),
                 (96, 122), (134, 122), (84, 118), (148, 96), (200, 160), (238, 164)]:
        lights.append(f'<rect x="{o+x}" y="{y}" width="3" height="2"/>')
    red = [(o + 282, 8), (o + 250, 24)] + [(x + 22, 112) for x in cranes]
    return f'''<g id="city">
<path fill="{p['far']}" d="{far}"/>
<path fill="{p['near']}" d="{' '.join(near)}"/>
<path stroke="{p['near']}" stroke-width="0.8" fill="none" d="{cables}"/>
<path fill="{p['glass']}" d="M{o+70} 128 V96 Q{o+80} 80 {o+92} 92 Q{o+104} 70 {o+120} 88 Q{o+132} 72 {o+146} 88 Q{o+158} 78 {o+168} 94 Q{o+172} 90 {o+176} 96 V128 Z"/>
<path stroke="{p['near']}" stroke-width="0.6" opacity="0.45" fill="none" d="M{o+70} 104 H{o+176} M{o+70} 112 H{o+176} M{o+70} 120 H{o+176}"/>
<rect x="{o+72}" y="132" width="102" height="50" fill="url(#quay)" opacity="{p['quay_op']}"/>
<g fill="{p['win']}" opacity="{p['win_op']}">{''.join(lights)}</g>
<circle cx="{o+221}" cy="101" r="3.2" fill="{p['glass']}"/>
<g fill="#ff5a4f" opacity="{p['red_op']}">{''.join(f'<circle cx="{x}" cy="{y}" r="1.4"/>' for x, y in red)}</g>
</g>'''


def cloud(color):
    return (f'<g fill="{color}"><ellipse cx="60" cy="46" rx="50" ry="20"/><ellipse cx="100" cy="32" rx="42" ry="28"/>'
            f'<ellipse cx="142" cy="44" rx="46" ry="21"/><ellipse cx="100" cy="54" rx="92" ry="14"/></g>')
