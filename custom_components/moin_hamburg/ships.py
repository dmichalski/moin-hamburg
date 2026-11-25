"""Ships in the harbour from AIS (aisstream.io): which big ships the picture shows.

Pure Python, standard library only, no Home Assistant imports. The integration passes every AIS message from the
harbour window to Harbour.feed(); Harbour.shown() says what to draw: a cruise ship lying at a terminal and a big
container ship under way. Ships come and go on their own: a ship whose last position is too old no longer counts.

The window covers the Elbe from the Altona cruise terminal past the Landungsbruecken and Steinwerder to the
HafenCity cruise centre. Nothing else is sent to aisstream.io than the API key and this window.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
from dataclasses import dataclass

URL = 'wss://stream.aisstream.io/v0/stream'
WINDOW = [[53.528, 9.915], [53.552, 10.012]]        # south-west and north-east corner, latitude and longitude
MESSAGE_TYPES = ['PositionReport', 'ShipStaticData']  # class A ships only: big ships, no sailing boats
KINDS = ('cruise', 'container')

# AIS ship types: 60-69 passenger ships, 70-79 cargo ships. Ferries and barges are short, so length decides.
PASSENGER, CARGO = range(60, 70), range(70, 80)
CRUISE_LENGTH = 150        # m
CONTAINER_LENGTH = 250     # m
MOORED = .5                # knots and less: lying at the terminal
UNDER_WAY = 2              # knots and more
# Moored ships report every three minutes, ships under way every few seconds.
MOORED_FRESH = dt.timedelta(minutes=15)
UNDER_WAY_FRESH = dt.timedelta(minutes=5)
FORGET = dt.timedelta(hours=6)  # a ship not heard of for this long goes


@dataclass(frozen=True)
class Vessel:
    mmsi: int
    name: str = ''
    ship_type: int | None = None
    length: int | None = None          # m, bow to stern
    speed: float | None = None         # knots over ground
    seen: dt.datetime | None = None    # last position report
    heard: dt.datetime | None = None   # last message of any kind


def subscription(key):
    """The first message on the socket; aisstream.io wants it within three seconds."""
    return {'APIKey': key, 'BoundingBoxes': [WINDOW], 'FilterMessageTypes': MESSAGE_TYPES}


class Harbour:
    def __init__(self):
        self.vessels: dict[int, Vessel] = {}

    def feed(self, message, now):
        """Take one message from aisstream.io; anything that is not a usable report is ignored."""
        if not isinstance(message, dict):
            return
        kind = message.get('MessageType')
        body = (message.get('Message') or {}).get(kind)
        if kind not in MESSAGE_TYPES or not isinstance(body, dict):
            return
        mmsi = _int(body.get('UserID')) or _int((message.get('MetaData') or {}).get('MMSI'))
        if not mmsi:
            return
        v = self.vessels.get(mmsi) or Vessel(mmsi)
        if kind == 'PositionReport':
            if body.get('Valid') is False:
                return
            speed = _float(body.get('Sog'))
            # 102.3 knots means "not available" in AIS
            v = dataclasses.replace(v, speed=speed if speed is not None and speed < 102.3 else None, seen=now)
        else:
            d = body.get('Dimension') or {}
            length = (_int(d.get('A')) or 0) + (_int(d.get('B')) or 0)
            v = dataclasses.replace(v, name=str(body.get('Name') or '').strip(), ship_type=_int(body.get('Type')),
                                    length=length or None)
        self.vessels[mmsi] = dataclasses.replace(v, heard=now)
        self.forget(now)

    def forget(self, now):
        for mmsi in [m for m, v in self.vessels.items() if now - v.heard > FORGET]:
            del self.vessels[mmsi]

    def shown(self, now):
        """The big ships to draw, as a frozenset of KINDS."""
        out = set()
        for v in self.vessels.values():
            if v.seen is None or v.speed is None or v.length is None or v.ship_type is None:
                continue
            age = now - v.seen
            if v.ship_type in PASSENGER and v.length >= CRUISE_LENGTH and v.speed <= MOORED and age <= MOORED_FRESH:
                out.add('cruise')
            if v.ship_type in CARGO and v.length >= CONTAINER_LENGTH and v.speed >= UNDER_WAY and age <= UNDER_WAY_FRESH:
                out.add('container')
        return frozenset(out)

    def summary(self, now):
        """For the diagnostics: ship names are public AIS data, but only the big ones are listed."""
        big = [v for v in self.vessels.values() if (v.length or 0) >= CRUISE_LENGTH]
        return {'vessels': len(self.vessels), 'shown': sorted(self.shown(now)),
                'big_ships': [{'name': v.name, 'type': v.ship_type, 'length': v.length, 'speed': v.speed,
                               'seen': v.seen.isoformat() if v.seen else None} for v in big]}


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
