"""Canvas geometry and colours of the twelve base scenes (time of day x weather)."""

# The canvas is 1200 x 844. A phone in portrait mode (background-size: cover)
# only sees the middle band of about 390 px, starting at OX: that is where the
# Elbphilharmonie, the Michel, the TV tower and the cranes stand. Tablets and
# desktops see more Speicherstadt to the left and more harbour to the right.
W, H = 1200, 844
OX = 405           # left edge of the phone band
BASE = 330         # waterline (bottom edge of the skyline)
SKY_TOP = 140      # top edge of the skyline group

# sky: gradient stops; far/near: silhouettes; glass: Elbphilharmonie glass;
# win/win_op: window light; quay_op: Kaispeicher windows; red_op: aircraft warning
# lights; water: gradient stops; shimmer: glitter on the Elbe;
# clouds: (colour, opacity, count); body: sun, evening_sun, moon or None
PALETTES = {
    'day-clear': dict(
        sky=[(0, '#2a6fb5'), (.5, '#5aa6e0'), (1, '#a9d6f2')], far='#6a8fb0', near='#1f3a55', glass='#9cc6e4',
        win='#ffffff', win_op=0, quay_op=.12, red_op=0,
        water=[(0, '#3a78a8'), (.5, '#285b86'), (1, '#1c4468')], shimmer=('#ffffff', .85),
        clouds=('#ffffff', .9, 3), body='sun'),
    'day-cloudy': dict(
        sky=[(0, '#56687c'), (.5, '#7e8fa1'), (1, '#a7b3c0')], far='#5d6c7b', near='#243240', glass='#7d8d9c',
        win='#ffe2a6', win_op=.15, quay_op=.1, red_op=.6,
        water=[(0, '#42505d'), (.55, '#2c3843'), (1, '#1f2830')], shimmer=('#dfe8f0', .4),
        clouds=('#8e9bab', .85, 7), body=None),
    'day-rain': dict(
        sky=[(0, '#3c4854'), (.42, '#5b6876'), (1, '#7a8692')], far='#3a4652', near='#1c252e', glass='#4c5a68',
        win='#ffd27a', win_op=.4, quay_op=.15, red_op=.9,
        water=[(0, '#2a3640'), (.55, '#1b242c'), (1, '#131a20')], shimmer=('#dce8f4', .4),
        clouds=('#4a5561', .88, 8), body=None, rain=True),
    'day-snow': dict(
        sky=[(0, '#647488'), (.5, '#9aa8b7'), (1, '#c9d2db')], far='#7f8c9a', near='#3e4a57', glass='#a9b6c3',
        win='#ffe2a6', win_op=.35, quay_op=.12, red_op=.6,
        water=[(0, '#6f7c89'), (.55, '#56626e'), (1, '#434e59')], shimmer=('#ffffff', .6),
        clouds=('#b3bdc8', .75, 6), body=None, snow=True),
    'dusk-clear': dict(
        sky=[(0, '#221f4a'), (.34, '#57386b'), (.68, '#c0605a'), (1, '#f2a765')], far='#4a2e4e', near='#1a1325',
        glass='#e7a06f', win='#ffcf86', win_op=.75, quay_op=.3, red_op=.9,
        water=[(0, '#5b3551'), (.55, '#2c1b30'), (1, '#180f1d')], shimmer=('#ffb86e', .8),
        clouds=('#f2a38a', .5, 3), body='evening_sun'),
    'dusk-cloudy': dict(
        sky=[(0, '#2b2848'), (.4, '#584460'), (.75, '#96646c'), (1, '#c08a74')], far='#4a3448', near='#1b1422',
        glass='#b98a78', win='#ffcf86', win_op=.7, quay_op=.28, red_op=.9,
        water=[(0, '#4a3446'), (.55, '#281c2a'), (1, '#160f19')], shimmer=('#f0a878', .55),
        clouds=('#8a6878', .8, 7), body=None),
    'dusk-rain': dict(
        sky=[(0, '#262a3f'), (.45, '#474860'), (1, '#77646e')], far='#3a3848', near='#16141f', glass='#6a6274',
        win='#ffcf86', win_op=.7, quay_op=.28, red_op=.9,
        water=[(0, '#35303f'), (.55, '#1f1b26'), (1, '#131017')], shimmer=('#e8b58a', .45),
        clouds=('#4d4a5e', .88, 8), body=None, rain=True),
    'dusk-snow': dict(
        sky=[(0, '#3b4560'), (.5, '#6d7890'), (1, '#a3a9bb')], far='#5d6780', near='#252c3d', glass='#8e97ad',
        win='#ffd9a0', win_op=.75, quay_op=.3, red_op=.9,
        water=[(0, '#4f5870'), (.55, '#343b4f'), (1, '#22283a')], shimmer=('#ffffff', .5),
        clouds=('#7e889e', .7, 6), body=None, snow=True),
    'night-clear': dict(
        sky=[(0, '#050918'), (.55, '#0f1936'), (1, '#1b2850')], far='#141c33', near='#04060d', glass='#1a2748',
        win='#ffd27a', win_op=1, quay_op=.45, red_op=1,
        water=[(0, '#0b1330'), (.55, '#070c1c'), (1, '#04070f')], shimmer=('#ffd27a', .85),
        clouds=None, body='moon', stars=True),
    'night-cloudy': dict(
        sky=[(0, '#0b1022'), (.55, '#161f38'), (1, '#222c48')], far='#182036', near='#05070e', glass='#1c2740',
        win='#ffd27a', win_op=1, quay_op=.45, red_op=1,
        water=[(0, '#0d142c'), (.55, '#080d1d'), (1, '#05080f')], shimmer=('#ffd27a', .7),
        clouds=('#232c44', .9, 7), body=None),
    'night-rain': dict(
        sky=[(0, '#0b1020'), (.55, '#171e33'), (1, '#252d44')], far='#1a2135', near='#05070e', glass='#1e283e',
        win='#ffd27a', win_op=1, quay_op=.45, red_op=1,
        water=[(0, '#0e1428'), (.55, '#090d1b'), (1, '#05080f')], shimmer=('#ffd27a', .6),
        clouds=('#252d42', .92, 8), body=None, rain=True),
    'night-snow': dict(
        sky=[(0, '#111a33'), (.55, '#1f2b4a'), (1, '#34405e')], far='#26314c', near='#070a14', glass='#2a3654',
        win='#ffd27a', win_op=1, quay_op=.45, red_op=1,
        water=[(0, '#18213c'), (.55, '#0f1629'), (1, '#090d1a')], shimmer=('#ffffff', .55),
        clouds=('#2e3956', .85, 6), body=None, snow=True),
}

# Theme colours per scene: (sky top, card, accent, opaque ground)
THEME_COLORS = {
    'day-clear':          ('#2a6fb5', 'rgba(14, 34, 56, 0.66)',  '#8fc8f0', '#16293d'),
    'day-cloudy':        ('#56687c', 'rgba(20, 28, 38, 0.66)',  '#b5c7d8', '#1f2a35'),
    'day-rain':         ('#3c4854', 'rgba(16, 24, 32, 0.66)',  '#a9d2ef', '#1b242c'),
    'day-snow':        ('#647488', 'rgba(24, 32, 44, 0.66)',  '#c6d6e6', '#222c38'),
    'dusk-clear':   ('#221f4a', 'rgba(26, 14, 32, 0.66)',  '#ffc38e', '#231a2e'),
    'dusk-cloudy': ('#2b2848', 'rgba(26, 18, 32, 0.66)',  '#f0b89a', '#241c2c'),
    'dusk-rain':  ('#262a3f', 'rgba(20, 18, 28, 0.66)', '#d9b8a8', '#1e1b28'),
    'dusk-snow': ('#3b4560', 'rgba(20, 24, 40, 0.66)',  '#c9d2ea', '#1f2437'),
    'night-clear':        ('#050918', 'rgba(10, 16, 38, 0.66)', '#b9c7ff', '#0d1428'),
    'night-cloudy':      ('#0b1022', 'rgba(12, 18, 36, 0.66)', '#aab8e0', '#0f1528'),
    'night-rain':       ('#0b1020', 'rgba(12, 18, 34, 0.66)', '#a9bde0', '#0f1527'),
    'night-snow':      ('#111a33', 'rgba(14, 22, 44, 0.66)', '#c6d2f0', '#141d36'),
}


def rgba(hex_color, alpha):
    h = hex_color.lstrip('#')
    return f'rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {alpha})'
