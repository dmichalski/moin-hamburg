"""Showcase, icon and READMEs: the example pictures are what the integration would draw, the page has what
it needs, the icon has the sizes Home Assistant expects, and the English and German READMEs say the same.

Runs with pytest or on its own: python3 tests/test_showcase.py
"""
import json
import pathlib
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'custom_components' / 'moin_hamburg'), str(ROOT / 'tools')]
sys.dont_write_bytecode = True

import render  # noqa: E402
import showcase  # noqa: E402
import state  # noqa: E402


def integration_form(key):
    """The key as state.update() would write it: moon only on clear nights, wind direction unless calm,
    extremes sorted."""
    p = render.parse_key(key)
    parts = key.split('.')
    wind = parts[2].split('-')
    extremes = [x for x in parts[3:] if x in render.EXTREMES]
    return ((p['moon'] is not None) == (p['scene'] == 'night-clear')
            and (len(wind) == 3) == (p['wind'] != 'calm')
            and extremes == sorted(extremes))


def test_every_special_day_has_an_example():
    assert set(showcase.DAYS) == set(state.PRECEDENCE)
    for day, (key, when, *title) in showcase.DAYS.items():
        assert render.parse_key(key)['day'] == day, key
        assert when.endswith('.'), day
        assert integration_form(key), key


def test_calendar_days_have_a_matching_title():
    for day, (_, _, *title) in showcase.DAYS.items():
        if day in state.KEYWORDS:
            assert title, f'{day}: no example title'
            assert state.match_title(title[0], state.KEYWORDS)[0] == day, title[0]
        else:
            assert not title, f'{day}: a title, but it is not a calendar day'


def test_reel_and_hero():
    for key in showcase.REEL + (showcase.HERO,):
        assert integration_form(key), key


def test_site_build():
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp)
        showcase.build_site(out, 'owner/moin-hamburg', with_gif=False)
        data = json.loads((out / 'data.json').read_text(encoding='utf-8'))
        assert [d['id'] for d in data['days']] == list(state.PRECEDENCE)
        assert all(d['name'] and d['name_de'] for d in data['days'])
        assert set(data['files']) == {p.name for p in (out / 'py' / 'render').glob('*.py')}
        assert {f'{t}-{w}' for t in data['times'] for w in data['weathers']} == set(data['colors'])
        for day in data['days']:
            ET.fromstring((out / 'days' / f'{day["id"]}.svg').read_text(encoding='utf-8'))
        for name in ('index.html', 'app.js', 'style.css', 'hero.svg'):
            assert (out / name).is_file(), name
        assert not (out / 'package.json').exists()
        assert re.fullmatch(r'https://cdn\.jsdelivr\.net/npm/pyodide@\d+\.\d+\.\d+/', data['pyodide']), data['pyodide']
        assert 'pyodide@' not in (out / 'app.js').read_text(encoding='utf-8'), 'the version belongs in site/package.json'
        page = (out / 'index.html').read_text(encoding='utf-8')
        for ref in ('style.css', 'app.js'):
            assert ref in page


def test_readmes_match():
    """Same headings, same table sizes, same code (comments aside) and same links in both languages."""
    en, de = ((ROOT / name).read_text(encoding='utf-8') for name in ('README.md', 'README.de.md'))
    parts = {
        'headings': lambda t: [line.split(' ')[0] for line in t.splitlines() if line.startswith('#')],
        'tables': lambda t: [len(b.strip().splitlines()) for b in re.findall(r'((?:^\|.*\n)+)', t, re.M)],
        'code': lambda t: [re.sub(r'#.*', '', b) for b in re.findall(r'```.*?```', t, re.S)],
        'links': lambda t: sorted(set(re.findall(r'https://[^)\s]+', t))),
    }
    for name, part in parts.items():
        assert part(en) == part(de), f'README.md and README.de.md differ in their {name}'
    assert '(README.de.md)' in en and '(README.md)' in de



def test_brand_icons():
    """brand/ holds the icon in the two sizes Home Assistant expects, as PNG with transparency (tools/brand.py)."""
    brand = ROOT / 'custom_components' / 'moin_hamburg' / 'brand'
    assert sorted(p.name for p in brand.iterdir()) == ['icon.png', 'icon@2x.png']
    for name, size in (('icon.png', 256), ('icon@2x.png', 512)):
        head = (brand / name).read_bytes()[:26]
        assert head[:8] == b'\x89PNG\r\n\x1a\n' and head[12:16] == b'IHDR', name
        width, height = int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')
        assert (width, height) == (size, size), f'{name} is {width} x {height}'
        assert head[25] == 6, f'{name} has no alpha channel'


if __name__ == '__main__':
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith('test_') and callable(f)]
    failed = 0
    for name, f in tests:
        try:
            f()
        except AssertionError as e:
            failed += 1
            print(f'FAIL {name}: {e}')
    print(f'{len(tests) - failed} of {len(tests)} tests passed')
    sys.exit(1 if failed else 0)
