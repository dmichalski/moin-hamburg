"""Moin Hamburg renderer: one SVG background per state key.

Pure Python, standard library only, no Home Assistant imports, so it runs in
the integration, on the command line, in tests and in the browser (Pyodide).

A state key describes everything the picture shows, for example

    night-cloudy.autumn.wind-calm.warning-storm-gusts
    day-rain.autumn.wind-storm-west.snow-cover.event-advent

Parts, separated by dots:

    <time of day>-<weather>   day, dusk, night - clear, cloudy, rain, snow
    <season>                  spring, summer, autumn, winter
    wind-<level>[-<from>]     calm, windy, storm; east or west (default west)
    moon-<0..7>               moon phase in eighths, 0 = new, 4 = full
    tide-<0..4>               the Elbe from mean low (0) to mean high tide (4);
                              without it the water stands as at high tide
    <extreme>                 heat, cold, snow-cover, fog, thunder, storm-surge,
                              ice-drift
    ship-<kind>               big ships from AIS: cruise (at the terminal),
                              container (under way)
    warning-<kind>            hurricane, storm-surge, storm-gusts, thunder, heat,
                              frost, snow; balls on the signal mast for storms
    event-<day>               a special day, see layers.PLAYFUL_DAYS

The first three are required, the rest optional and in any order. The same key
always gives the same picture: the key is the random seed. state.update() makes
the key from weather, sun, warnings and calendars.
"""
import re

from . import layers as _layers
from . import scene as _scene
from .palette import PALETTES, THEME_COLORS, TIDE_STEPS, rgba

SEASONS = ('spring', 'summer', 'autumn', 'winter')
WINDS = ('calm', 'windy', 'storm')
EXTREMES = ('heat', 'cold', 'snow-cover', 'fog', 'thunder', 'storm-surge', 'ice-drift')
SHIPS = ('cruise', 'container')
KEY_PATTERN = re.compile(r'[a-z0-9.-]{3,200}')


class InvalidKey(ValueError):
    """The state key cannot be drawn."""


def parse_key(key):
    """Split a state key into its parts; raises InvalidKey."""
    if not KEY_PATTERN.fullmatch(key):
        raise InvalidKey('key contains characters other than a-z, 0-9, dot and dash')
    parts = key.split('.')
    if len(parts) < 3 or parts[0] not in PALETTES or parts[1] not in SEASONS:
        raise InvalidKey('unknown scene or season')
    w = parts[2].split('-')
    if w[0] != 'wind' or len(w) not in (2, 3) or w[1] not in WINDS or (len(w) == 3 and w[2] not in ('east', 'west')):
        raise InvalidKey('invalid wind part')
    state = {'scene': parts[0], 'season': parts[1], 'wind': w[1], 'direction': -1 if len(w) == 3 and w[2] == 'east' else 1,
             'moon': None, 'tide': None, 'extremes': [], 'ships': [], 'warning': 'none', 'day': 'none'}
    for p in parts[3:]:
        if p.startswith('moon-') and p[5:].isdigit() and int(p[5:]) < 8:
            state['moon'] = int(p[5:])
        elif p.startswith('tide-') and p[5:].isdigit() and int(p[5:]) <= TIDE_STEPS:
            state['tide'] = int(p[5:])
        elif p in EXTREMES:
            state['extremes'].append(p)
        elif p.startswith('ship-') and p[5:] in SHIPS:
            state['ships'].append(p[5:])
        elif p.startswith('warning-') and len(p) > 8:
            state['warning'] = p[8:]
        elif p.startswith('event-') and len(p) > 6:
            state['day'] = p[6:]
        else:
            raise InvalidKey(f'unknown part: {p}')
    return state


def render(key, animated=True):
    """The background for a state key as SVG text."""
    s = parse_key(key)
    tod, weather = s['scene'].split('-')
    ctx = _layers.Context(tod, weather, s['season'], s['wind'], s['direction'], s['moon'], s['extremes'],
                          s['warning'], s['day'], animated, key, tide=s['tide'], ships=s['ships'])
    fragments = _layers.layers(ctx, PALETTES[s['scene']])
    return _scene.compose(s['scene'], animated, wind=s['wind'], direction=s['direction'], moon=s['moon'],
                          tide=s['tide'], css=_layers.LAYER_CSS, **fragments)


def moving_parts(svg):
    """Number of elements with a CSS class: a measure of how hard the browser works."""
    return svg.count('class="')


def theme_yaml(scene, image_url, still_image_url, names, header=''):
    """Theme YAML for both themes (animated, still) pointing at the given images.

    Dark mode only: a theme that defines nothing but modes.dark switches the
    frontend to dark mode on every device, which the glass cards need.
    """
    top, card, accent, ground = THEME_COLORS[scene]
    out = [header] if header else []
    for name, url in zip(names, (image_url, still_image_url)):
        v = {
            'lovelace-background': f'center / cover no-repeat url("{url}") fixed',
            'primary-background-color': ground, 'secondary-background-color': ground, 'card-background-color': ground,
            'sidebar-background-color': ground, 'app-header-background-color': rgba(top, 0.45),
            'app-header-text-color': '#ffffff', 'app-header-backdrop-filter': 'blur(12px)',
            'ha-card-background': card, 'ha-card-border-color': 'rgba(255, 255, 255, 0.13)', 'ha-card-border-width': '1px',
            'ha-card-border-radius': '18px', 'ha-card-box-shadow': 'none', 'primary-text-color': '#f4f6f8',
            'secondary-text-color': 'rgba(244, 246, 248, 0.74)', 'divider-color': 'rgba(255, 255, 255, 0.12)',
            'primary-color': accent, 'accent-color': accent, 'state-icon-color': accent,
            'weather-icon-sun-color': '#ffd262', 'weather-icon-moon-color': '#f3efd9',
            'weather-icon-cloud-front-color': '#e8eef5', 'weather-icon-cloud-back-color': '#9fb0c2', 'weather-icon-rain-color': accent,
        }
        out.append('\n'.join([f'{name}:', '  modes:', '    dark:'] + [f"      {k}: '{w}'" for k, w in v.items()]))
    return '\n\n'.join(out) + '\n'
