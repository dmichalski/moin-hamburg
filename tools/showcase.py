#!/usr/bin/env python3
"""Build the showcase: the GitHub Pages site and the README animation.

    showcase.py site OUTDIR             the site, with the animation if Chrome is there
    showcase.py site OUTDIR --no-gif    the site without the animation
    showcase.py gif FILE                only the animation

The site runs the real renderer in the browser (Pyodide); this script copies
it next to the page together with the data the page needs and a still picture
for every special day. The animation needs Google Chrome (headless) to turn the
SVGs into pictures and Pillow to join them into a GIF.
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PKG = ROOT / 'custom_components' / 'moin_hamburg'
SITE = ROOT / 'site'
sys.dont_write_bytecode = True
sys.path.insert(0, str(PKG))

import render  # noqa: E402
import state  # noqa: E402
from render.palette import PALETTES, THEME_COLORS  # noqa: E402

# The README animation: one still per picture, cropped to sky, skyline and reflection.
REEL = (
    'day-clear.summer.wind-calm',
    'day-clear.spring.wind-windy-west.event-harbour-birthday',
    'day-rain.autumn.wind-windy-west.tide-1',
    'day-cloudy.autumn.wind-storm-west.warning-storm-gusts',
    'night-cloudy.autumn.wind-calm.event-dom',
    'dusk-cloudy.autumn.wind-calm.event-st-martin',
    'day-snow.winter.wind-calm.snow-cover',
    'dusk-clear.winter.wind-calm.snow-cover.event-christmas',
    'night-clear.winter.wind-calm.moon-5.event-new-years-eve',
    'night-clear.spring.wind-calm.moon-4.event-cherry-blossom',
    'day-clear.summer.wind-windy-east.event-pride',
    'dusk-clear.summer.wind-calm.heat',
)
FRAME_MS = 1800
CROP = (0, 40, 1200, 470)
WIDTH = 960

# Every special day: an example picture, when it shows, and for the calendar
# days an event title that matches a default keyword.
DAYS = {
    'quiet': ('day-cloudy.spring.wind-calm.event-quiet',
              'Good Friday, Remembrance Sunday and the Sunday of the Dead. Wins over everything and keeps the picture calm.'),
    'birthday': ('day-clear.summer.wind-calm.event-birthday',
                 'An event in your calendars, by keyword. The name goes into the greeting, never into the picture.',
                 'Geburtstag Kim'),
    'new-years-eve': ('night-clear.winter.wind-calm.moon-5.event-new-years-eve', '31 December from 18:00 to 1 January 2:00.'),
    'new-years-day': ('day-cloudy.winter.wind-calm.event-new-years-day', '1 January from 2:00 to noon.'),
    'epiphany': ('dusk-clear.winter.wind-calm.event-epiphany', '6 January.'),
    'valentines': ('dusk-clear.winter.wind-calm.event-valentines', '14 February.'),
    'carnival': ('day-cloudy.winter.wind-windy-west.event-carnival', 'Rose Monday and Shrove Tuesday.'),
    'easter': ('day-clear.spring.wind-calm.event-easter', 'Holy Saturday to Easter Monday.'),
    'ascension': ('day-clear.spring.wind-calm.event-ascension', 'Ascension Day.'),
    'mothers-day': ('day-clear.spring.wind-calm.event-mothers-day', 'The second Sunday in May.'),
    'halloween': ('night-cloudy.autumn.wind-windy-west.event-halloween', '31 October.'),
    'st-martin': ('dusk-cloudy.autumn.wind-calm.event-st-martin', '11 November.'),
    'st-nicholas': ('dusk-clear.winter.wind-calm.event-st-nicholas', '6 December.'),
    'christmas': ('night-snow.winter.wind-calm.snow-cover.event-christmas', '24 to 26 December.'),
    'clock-change': ('day-cloudy.spring.wind-calm.event-clock-change',
                     'The last Sunday of March and of October.'),
    'harbour-birthday': ('day-clear.spring.wind-windy-west.event-harbour-birthday',
                         'An event in your calendars, by keyword.', 'Hafengeburtstag'),
    'cherry-blossom': ('night-clear.spring.wind-calm.moon-4.event-cherry-blossom',
                       'An event in your calendars, by keyword.', 'Kirschblütenfest'),
    'pride': ('day-clear.summer.wind-windy-east.event-pride', 'An event in your calendars, by keyword.', 'CSD Hamburg'),
    'blue-port': ('night-clear.summer.wind-calm.moon-0.event-blue-port', 'An event in your calendars, by keyword.', 'Blue Port'),
    'solstice': ('dusk-clear.summer.wind-calm.event-solstice', '20 to 22 June.'),
    'shooting-stars': ('night-clear.summer.wind-calm.moon-0.event-shooting-stars',
                       '10 to 14 August and 12 to 15 December, after dark.'),
    'first-snow': ('day-snow.winter.wind-calm.event-first-snow',
                   'The day it first snows for 15 minutes, October to April, once a winter.'),
    'match-st-pauli': ('night-cloudy.autumn.wind-calm.event-match-st-pauli',
                       'An event in your calendars, by keyword, while it lasts: the floodlights of the Millerntor, just '
                       'behind the Elbphilharmonie. Fixture lists name the home side first, so the keywords find the home '
                       'matches.', 'FC St. Pauli – Werder Bremen'),
    'match-hsv': ('dusk-clear.spring.wind-calm.event-match-hsv',
                  'An event in your calendars, by keyword, while it lasts: the floodlights of the Volksparkstadion, '
                  'far off in the west.', 'Hamburger SV – Hertha BSC'),
    'dom': ('night-cloudy.autumn.wind-calm.event-dom', 'An event in your calendars, by keyword.', 'Winterdom'),
    'school-holidays': ('day-clear.summer.wind-calm.event-school-holidays',
                        'An event in your calendars, by keyword.', 'Herbstferien'),
    'advent': ('dusk-cloudy.winter.wind-calm.event-advent', 'First Advent to 23 December.'),
    'bin-day': ('day-cloudy.autumn.wind-calm.event-bin-day',
                'Any event in a bin collection calendar today, from 6 to 10 in the morning.'),
}
HERO = 'dusk-clear.summer.wind-calm.event-harbour-birthday'


def _translations(lang):
    data = json.loads((PKG / 'translations' / f'{lang}.json').read_text(encoding='utf-8'))
    return data['entity']['sensor']['special_day']['state']


def site_data(repo):
    """Everything the page needs besides the renderer itself."""
    en, de = _translations('en'), _translations('de')
    days = []
    for day in state.PRECEDENCE:
        key, when, *title = DAYS[day]
        days.append({'id': day, 'name': en[day], 'name_de': de[day], 'when': when, 'key': key,
                     'keywords': list(state.KEYWORDS.get(day, ())), 'title': title[0] if title else ''})
    scenes = sorted(PALETTES)
    return {
        'repo': repo,
        'version': json.loads((PKG / 'manifest.json').read_text())['version'],
        'times': [t for t in ('day', 'dusk', 'night') if any(s.startswith(t + '-') for s in scenes)],
        'weathers': [w for w in ('clear', 'cloudy', 'rain', 'snow') if any(s.endswith('-' + w) for s in scenes)],
        'seasons': list(render.SEASONS), 'winds': list(render.WINDS), 'extremes': list(render.EXTREMES),
        'ships': list(render.SHIPS),
        'warnings': [kind for kind, _ in state.WARNINGS],
        'colors': {s: dict(zip(('top', 'card', 'accent', 'ground'), THEME_COLORS[s])) for s in scenes},
        'days': days, 'hero': HERO, 'texts': state.TEXTS['en'],
        'files': sorted(p.name for p in (PKG / 'render').glob('*.py')),
        # in the file URLs, so a browser never mixes renderer files of two versions from its cache
        'build': hashlib.sha256(b''.join(p.read_bytes() for p in sorted((PKG / 'render').glob('*.py')))).hexdigest()[:12],
        'pyodide': f'https://cdn.jsdelivr.net/npm/pyodide@{pyodide_version()}/',
    }


def pyodide_version():
    """The Pyodide the page loads: pinned in site/package.json, where Dependabot updates it."""
    return json.loads((SITE / 'package.json').read_text(encoding='utf-8'))['dependencies']['pyodide']


def build_site(out, repo, with_gif):
    out.mkdir(parents=True, exist_ok=True)
    for f in SITE.iterdir():
        if f.is_file() and f.name != 'package.json':
            shutil.copy2(f, out / f.name)
    py = out / 'py' / 'render'
    py.mkdir(parents=True, exist_ok=True)
    for f in (PKG / 'render').glob('*.py'):
        shutil.copy2(f, py / f.name)
    data = site_data(repo)
    (out / 'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    (out / 'days').mkdir(exist_ok=True)
    for day in data['days']:
        (out / 'days' / f'{day["id"]}.svg').write_text(render.render(day['key'], False), encoding='utf-8')
    (out / 'hero.svg').write_text(render.render(HERO, True), encoding='utf-8')
    if with_gif:
        build_gif(out / 'showcase.gif')
    print(f'site in {out}' + (' with the animation' if with_gif else ''))


def _chrome():
    for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome'):
        if path := shutil.which(name):
            return path
    raise SystemExit('no Chrome or Chromium found for the animation; use --no-gif')


def build_gif(path):
    from PIL import Image
    chrome = _chrome()
    # GitHub's Ubuntu runners do not allow Chrome's sandbox; the pages are our own SVGs.
    extra = ['--no-sandbox'] if os.environ.get('CI') else []
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, key in enumerate(REEL):
            svg, png = pathlib.Path(tmp, f'{i}.svg'), pathlib.Path(tmp, f'{i}.png')
            svg.write_text(render.render(key, False), encoding='utf-8')
            subprocess.run([chrome, '--headless', '--disable-gpu', '--hide-scrollbars', *extra,
                            '--window-size=1200,844', f'--screenshot={png}', svg.as_uri()],
                           check=True, capture_output=True, timeout=120)
            with Image.open(png) as im:
                band = im.convert('RGB').crop(CROP)
            band = band.resize((WIDTH, round(WIDTH * (CROP[3] - CROP[1]) / (CROP[2] - CROP[0]))), Image.Resampling.LANCZOS)
            frames.append(band.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG))
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=FRAME_MS, loop=0, optimize=True)
    print(f'{path}: {len(frames)} pictures, {path.stat().st_size // 1024} KB')


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('site')
    s.add_argument('out', type=pathlib.Path)
    s.add_argument('--no-gif', action='store_true')
    s.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY', 'dmichalski/moin-hamburg'))
    g = sub.add_parser('gif')
    g.add_argument('file', type=pathlib.Path)
    a = ap.parse_args(argv)
    if a.cmd == 'site':
        build_site(a.out, a.repo, not a.no_gif)
    else:
        build_gif(a.file)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
