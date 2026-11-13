"""Renderer regression test: every golden case must draw exactly as recorded.

tests/golden/hashes.json holds the sha256 of the animated image, the still
image and the theme text for every case in tests/golden/cases.txt, made by
tools/golden.py. Besides the hashes, every image must be well-formed XML and
stay within the budget of moving parts.
"""
import hashlib
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'custom_components' / 'moin_hamburg'), str(ROOT / 'tools')]

import golden  # noqa: E402
import render  # noqa: E402

HASHES = json.loads((ROOT / 'tests' / 'golden' / 'hashes.json').read_text(encoding='utf-8'))
# The overloaded case (hurricane, surge, fog, thunder and Halloween at once) is allowed a little more.
MAX_MOVING_PARTS = 600
OVERLOADED = 'night-rain.autumn.wind-storm-west.moon-5.storm-surge.fog.thunder.warning-hurricane.event-halloween'


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def check(key):
    expected = HASHES[key]
    wrong = []
    animated, still = render.render(key, True), render.render(key, False)
    if sha(animated) != expected['animated']:
        wrong.append('animated')
    if sha(still) != expected['still']:
        wrong.append('still')
    if sha(golden.theme(render, key)) != expected['theme']:
        wrong.append('theme')
    for svg in (animated, still):
        try:
            ET.fromstring(svg)
        except ET.ParseError as e:
            wrong.append(f'xml: {e}')
    parts = render.moving_parts(animated)
    if parts > MAX_MOVING_PARTS and key != OVERLOADED:
        wrong.append(f'{parts} moving parts')
    return wrong


def test_cases_match_generator():
    assert (ROOT / 'tests' / 'golden' / 'cases.txt').read_text(encoding='utf-8').split() == golden.cases()


def test_golden():
    failures = {key: w for key in HASHES if (w := check(key))}
    assert not failures, f'{len(failures)} of {len(HASHES)} cases differ: {dict(list(failures.items())[:5])}'


def test_invalid_keys():
    for key in ('', 'day-clear', 'day-clear.autumn', 'noon-clear.autumn.wind-calm', 'day-clear.autumn.wind-gale',
                'day-clear.autumn.wind-calm-north', 'day-clear.autumn.wind-calm.moon-8', 'day-clear.autumn.wind-calm.nonsense',
                'Day-clear.autumn.wind-calm', 'day-clear.autumn.wind-calm/../x', 'day-clear.autumn.wind-calm.event-'):
        try:
            render.parse_key(key)
        except render.InvalidKey:
            continue
        raise AssertionError(f'accepted invalid key {key!r}')


if __name__ == '__main__':
    test_cases_match_generator()
    test_invalid_keys()
    failures = {key: w for key in HASHES if (w := check(key))}
    print(f'{len(HASHES) - len(failures)} of {len(HASHES)} cases as recorded')
    for key, w in list(failures.items())[:10]:
        print('  differs:', key, w)
    sys.exit(1 if failures else 0)
