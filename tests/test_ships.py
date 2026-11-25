"""Big ships from AIS: which reports count, and what the picture shows.

Runs with pytest or on its own: python3 tests/test_ships.py
"""
import datetime as dt
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'custom_components' / 'moin_hamburg')]
sys.dont_write_bytecode = True

import ships  # noqa: E402

NOON = dt.datetime(2027, 5, 1, 12, 0, tzinfo=dt.timezone.utc)


def static(mmsi, ship_type, length, name='SHIP'):
    return {'MessageType': 'ShipStaticData', 'MetaData': {'MMSI': mmsi},
            'Message': {'ShipStaticData': {'UserID': mmsi, 'Name': name + '   ', 'Type': ship_type, 'Valid': True,
                                           'Dimension': {'A': length - 40, 'B': 40, 'C': 15, 'D': 15}}}}


def position(mmsi, sog, valid=True):
    return {'MessageType': 'PositionReport', 'MetaData': {'MMSI': mmsi},
            'Message': {'PositionReport': {'UserID': mmsi, 'Sog': sog, 'Latitude': 53.54, 'Longitude': 9.96,
                                           'Valid': valid}}}


def harbour(*messages, now=NOON):
    h = ships.Harbour()
    for m in messages:
        h.feed(m, now)
    return h


def test_cruise_ship_at_the_terminal():
    h = harbour(static(1, 60, 300, 'AIDAPRIMA'), position(1, .1))
    assert h.shown(NOON) == {'cruise'}
    assert h.shown(NOON + dt.timedelta(minutes=15)) == {'cruise'}
    assert h.shown(NOON + dt.timedelta(minutes=16)) == frozenset()            # no position for too long
    assert harbour(static(1, 60, 300), position(1, 8)).shown(NOON) == frozenset()     # leaving
    assert harbour(static(1, 60, 60), position(1, 0)).shown(NOON) == frozenset()      # a harbour ferry


def test_container_ship_under_way():
    h = harbour(position(2, 9.5), static(2, 71, 366))                       # the order does not matter
    assert h.shown(NOON) == {'container'}
    assert h.shown(NOON + dt.timedelta(minutes=6)) == frozenset()
    assert harbour(static(2, 71, 366), position(2, 0)).shown(NOON) == frozenset()     # at the quay
    assert harbour(static(2, 79, 120), position(2, 9)).shown(NOON) == frozenset()     # a feeder
    assert harbour(static(2, 52, 300), position(2, 9)).shown(NOON) == frozenset()     # a tug, whatever it says


def test_both_and_bad_reports():
    h = harbour(static(1, 60, 300), position(1, 0), static(2, 70, 400), position(2, 12))
    assert h.shown(NOON) == {'cruise', 'container'}
    assert harbour(static(3, 60, 300), position(3, 102.3)).shown(NOON) == frozenset()   # speed unknown
    assert harbour(static(3, 60, 300), position(3, 0, valid=False)).shown(NOON) == frozenset()
    for junk in (None, [], {}, {'MessageType': 'PositionReport'}, {'MessageType': 'SubscriptionConfirmation',
                                                                     'Message': {'CompressionEnabled': True}},
                 {'MessageType': 'PositionReport', 'Message': {'PositionReport': {'Sog': 'fast'}}}):
        h.feed(junk, NOON)
    assert len(h.vessels) == 2


def test_ships_are_forgotten():
    h = harbour(static(1, 60, 300), position(1, 0))
    h.forget(NOON + dt.timedelta(hours=6))
    assert 1 in h.vessels
    h.forget(NOON + dt.timedelta(hours=6, seconds=1))
    assert h.vessels == {}


def test_subscription_and_summary():
    sub = ships.subscription('k')
    assert sub == {'APIKey': 'k', 'BoundingBoxes': [ships.WINDOW], 'FilterMessageTypes': ['PositionReport', 'ShipStaticData']}
    (south, west), (north, east) = ships.WINDOW
    assert south < 53.5446 < north and west < 9.9686 < east                # the Landungsbruecken
    s = harbour(static(1, 60, 300, 'AIDAPRIMA'), position(1, 0), static(5, 31, 30, 'TUG'), position(5, 3)).summary(NOON)
    assert s['vessels'] == 2 and s['shown'] == ['cruise'] and [b['name'] for b in s['big_ships']] == ['AIDAPRIMA']


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
