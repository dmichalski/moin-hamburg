#!/usr/bin/env python3
"""Golden test data for the renderer.

    golden.py cases    write tests/golden/cases.txt
    golden.py hashes   write tests/golden/hashes.json from the current renderer

The cases cover every scene, season, wind level and direction, moon phase,
tide step, extreme, warning and special day at least once, by day, at dusk and
at night.

Regenerate the hashes only for an intended visual change, and look at the
pictures before committing them (tools/gallery.py).
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = ROOT / 'tests' / 'golden'
THEME_NAMES = ('moin-hamburg', 'moin-hamburg-still')
THEME_URL = '/local/moin_hamburg'

SCENES = [f'{t}-{w}' for t in ('day', 'dusk', 'night') for w in ('clear', 'cloudy', 'rain', 'snow')]
SEASONS = ('spring', 'summer', 'autumn', 'winter')
WINDS = ('wind-calm', 'wind-windy', 'wind-windy-east', 'wind-storm', 'wind-storm-east')
EXTREMES = {'heat': 'summer', 'cold': 'winter', 'snow-cover': 'winter', 'fog': 'autumn',
            'thunder': 'summer', 'storm-surge': 'autumn', 'ice-drift': 'winter'}
WARNINGS = ('storm-gusts', 'hurricane', 'storm-surge', 'thunder', 'heat', 'frost', 'snow')
EVENTS = {'quiet': 'spring', 'new-years-eve': 'winter', 'new-years-day': 'winter', 'epiphany': 'winter',
          'valentines': 'winter', 'carnival': 'winter', 'clock-change': 'spring', 'easter': 'spring',
          'ascension': 'spring', 'mothers-day': 'spring', 'halloween': 'autumn', 'st-martin': 'autumn',
          'st-nicholas': 'winter', 'christmas': 'winter', 'birthday': 'summer', 'harbour-birthday': 'spring',
          'cherry-blossom': 'spring', 'pride': 'summer', 'blue-port': 'summer', 'dom': 'autumn',
          'school-holidays': 'summer', 'bin-day': 'autumn', 'advent': 'winter', 'solstice': 'summer',
          'shooting-stars': 'summer', 'first-snow': 'autumn'}


def cases():
    out = []
    for i, scene in enumerate(SCENES):
        for j, season in enumerate(SEASONS):
            out.append(f'{scene}.{season}.{WINDS[(i + j) % len(WINDS)]}')
    for m in range(8):
        out.append(f'night-clear.autumn.wind-calm.moon-{m}')
    out += ['dusk-cloudy.winter.wind-windy.moon-4', 'night-rain.spring.wind-storm-east.moon-2']
    for t in range(5):
        out.append(f'{SCENES[t * 2 + 1]}.{SEASONS[t % 4]}.{WINDS[t]}.tide-{t}')
    out += ['night-clear.autumn.wind-calm.moon-4.tide-0', 'dusk-clear.summer.wind-calm.tide-1.event-harbour-birthday',
            'day-snow.winter.wind-windy.tide-0.cold.snow-cover', 'night-rain.autumn.wind-storm.tide-4.storm-surge',
            'night-snow.winter.wind-calm.tide-1.cold.ice-drift.snow-cover']
    for ex, season in EXTREMES.items():
        for scene in ('day-clear', 'night-clear', 'dusk-cloudy'):
            out.append(f'{scene}.{season}.wind-windy.{ex}')
    for w in WARNINGS:
        out.append(f'day-cloudy.autumn.wind-storm.warning-{w}')
        out.append(f'night-rain.autumn.wind-windy-east.warning-{w}')
    for event, season in EVENTS.items():
        for scene in ('day-clear', 'dusk-clear', 'night-clear'):
            out.append(f'{scene}.{season}.wind-calm.event-{event}')
        out.append(f'night-snow.{season}.wind-windy-east.moon-3.event-{event}')
    out += [
        'night-rain.autumn.wind-storm-west.moon-5.storm-surge.fog.thunder.warning-hurricane.event-halloween',
        'day-snow.winter.wind-windy.cold.snow-cover.warning-frost.event-christmas',
        'dusk-clear.summer.wind-calm.heat.thunder.event-pride',
        'night-cloudy.autumn.wind-calm.warning-storm-gusts',
        'night-cloudy.autumn.wind-calm.event-dom',
    ]
    return out


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def theme(render, key):
    return render.theme_yaml(key.split('.')[0], f'{THEME_URL}/{key}.svg', f'{THEME_URL}/{key}-still.svg', THEME_NAMES)


def main(argv):
    if argv == ['cases']:
        GOLDEN.mkdir(parents=True, exist_ok=True)
        c = cases()
        assert len(c) == len(set(c)), 'duplicate cases'
        (GOLDEN / 'cases.txt').write_text('\n'.join(c) + '\n', encoding='utf-8')
        print(f'{len(c)} cases')
        return 0
    if argv == ['hashes']:
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ROOT / 'custom_components' / 'moin_hamburg'))
        import render
        result = {}
        for key in (GOLDEN / 'cases.txt').read_text(encoding='utf-8').split():
            result[key] = {'animated': sha(render.render(key, True)), 'still': sha(render.render(key, False)),
                           'theme': sha(theme(render, key))}
        (GOLDEN / 'hashes.json').write_text(json.dumps(result, indent=1, sort_keys=True) + '\n', encoding='utf-8')
        print(f'{len(result)} cases hashed')
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
