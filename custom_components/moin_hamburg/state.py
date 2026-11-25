"""Moin Hamburg state: what the skyline shows right now.

Pure Python, standard library only, no Home Assistant imports. The integration
reads weather, sun, warnings, calendars and the water level from Home Assistant
and passes them in as plain values; update() returns the state key for the
renderer and the texts for the dashboard header, plus the memory to keep for
the next update.

Units: temperatures in degrees Celsius, wind in km/h, water level in cm above
the gauge zero at Hamburg St. Pauli. Times are aware
datetimes; `now` carries the local time zone.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import functools
import math
import re
from dataclasses import dataclass, field

# Weather conditions as Home Assistant names them.
RAIN = frozenset({'rainy', 'pouring', 'lightning', 'lightning-rainy'})
SNOW = frozenset({'snowy', 'snowy-rainy', 'hail'})
WET = RAIN | SNOW
CLOUDS = frozenset({'cloudy', 'fog', 'windy-variant', 'exceptional'})
THUNDER = frozenset({'lightning', 'lightning-rainy'})
SNOWFALL = frozenset({'snowy', 'snowy-rainy'})

# Wind: gusts if the weather service has them, otherwise the mean wind.
GUSTS_WINDY, GUSTS_STORM = 40, 75
MEAN_WINDY, MEAN_STORM = 29, 62

HEAT, COLD = 30, -8
SNOW_COVER_ON = (1, dt.timedelta(hours=2))   # snowing at or below 1 degree for two hours
SNOW_COVER_OFF = (3, dt.timedelta(hours=6))  # above 3 degrees for six hours
FIRST_SNOW = dt.timedelta(minutes=15)        # snowing for 15 minutes, October to April
FIRST_SNOW_MONTHS = (10, 11, 12, 1, 2, 3, 4)
# Ice drift on the Elbe: after four days of frost without a single reading above
# 0 degrees the river carries pack ice; it goes once two days have passed without frost.
ICE_DRIFT_ON = (0, dt.timedelta(days=4))
ICE_DRIFT_OFF = dt.timedelta(days=2)
# Updates come every 15 minutes or sooner. After a longer gap (Home Assistant
# was down) nobody knows what the weather did: the snow and ice clocks start again.
GAP = dt.timedelta(hours=1)

# Weather warnings, by headline. The first kind that matches any warning in
# force wins. German first (DWD, NINA), English as DWD and others word it.
WARNINGS = (
    ('hurricane', r'ORKAN|HURRICANE'),
    ('storm-surge', r'STURMFLUT|STORM SURGE'),
    ('storm-gusts', r'STURM|GALE|(?<!THUNDER)STORM'),
    ('thunder', r'GEWITTER|THUNDER'),
    ('heat', r'HITZE|HEAT'),
    ('frost', r'STRENGE[MNR]? FROST|STRONG FROST|SEVERE FROST'),
    ('snow', r'SCHNEE|SNOW'),
)
# Warnings come and go: the DWD renews them every few hours, and between two
# issues the feed may be empty for up to 20 minutes. The picture keeps the last
# warning until none has been seen for this long.
WARNING_HOLD = dt.timedelta(minutes=30)

# Water level at the gauge Hamburg St. Pauli (PEGELONLINE, station 5952050), in cm above its gauge
# zero (NHN -5.004 m). Mean low and high tide of 2001-2010 as the gauge lists them. A storm surge, as the
# BSH counts it, starts 1.5 m above mean high tide; it ends 10 cm below that, so the picture does not flicker.
MEAN_LOW_TIDE, MEAN_HIGH_TIDE = 347, 711
STORM_SURGE = MEAN_HIGH_TIDE + 150
STORM_SURGE_END = STORM_SURGE - 10
# The picture shows the tide in steps from mean low (0) to mean high tide (4). A new step needs the water
# a little past the middle between two steps, so a level standing at the boundary keeps its picture.
TIDE_STEPS = 4
TIDE_MARGIN = .15  # of a step
# A gauge that does not answer keeps its last picture for this long.
WATER_HOLD = dt.timedelta(hours=1)

# Big ships from AIS (ships.py decides which ones count).
SHIPS = ('cruise', 'container')

# Special days, most important first. Only one is drawn: a quiet day (Good
# Friday, the days of remembrance in November) wins over everything and keeps
# the picture calm, then a birthday, then single days, then periods (Dom,
# school holidays, Advent), then the bin lorry.
PRECEDENCE = (
    'quiet', 'birthday',
    'new-years-eve', 'new-years-day', 'epiphany', 'valentines', 'carnival', 'easter', 'ascension', 'mothers-day',
    'halloween', 'st-martin', 'st-nicholas', 'christmas', 'clock-change',
    'harbour-birthday', 'cherry-blossom', 'pride', 'blue-port', 'solstice', 'shooting-stars', 'first-snow',
    'match-st-pauli', 'match-hsv',
    'dom', 'school-holidays', 'advent',
    'bin-day',
)
# Days that come from the user's calendars, found by the event title. A keyword
# matches the start of the title up to a word boundary, ignoring case; * stands
# for any text. Birthdays take the name from the rest of the title.
KEYWORDS = {
    'birthday': ('Geburtstag', 'Birthday', "*'s birthday"),
    'harbour-birthday': ('Hafengeburtstag', 'Harbour birthday', 'Port anniversary'),
    'cherry-blossom': ('Kirschblütenfest', 'Cherry blossom festival'),
    'pride': ('CSD', 'Pride'),
    'blue-port': ('Blue Port',),
    'dom': ('Dom', 'Hamburger Dom', 'Frühlingsdom', 'Sommerdom', 'Winterdom'),
    'school-holidays': ('*ferien', 'School holidays'),
    # Fixture lists put the home side first, so these find the home matches only.
    'match-st-pauli': ('FC St. Pauli', 'Heimspiel St. Pauli', 'Millerntor'),
    'match-hsv': ('Hamburger SV', 'HSV', 'Heimspiel HSV', 'Volksparkstadion'),
}
BIN_HOURS = (6, 10)  # the bin lorry shows from 6 to 10 on collection days

TEXTS = {
    'de': {
        'night': 'Gute Nacht', 'morning': 'Guten Morgen', 'day': 'Guten Tag', 'evening': 'Guten Abend',
        'birthday': 'Alles Gute, {name}!', 'birthday-anonymous': 'Alles Gute zum Geburtstag!',
        'new-years-eve': 'Guten Rutsch!', 'new-years-day': 'Frohes neues Jahr!', 'easter': 'Frohe Ostern',
        'halloween': 'Süßes oder Saures?', 'christmas': 'Frohe Weihnachten', 'first-snow': 'Es schneit!',
        'rain': 'Regen', 'snow': 'Schnee', 'lasting': '{t}° · {wet}, hält noch an',
        'until': '{t}° · {wet} bis etwa {h} Uhr, danach trocken', 'from': '{t}° · ab {h} Uhr {wet}',
        'clear-night': 'Klar', 'clear-day': 'Heiter', 'cloudy': 'Bewölkt',
        'later': '{t}° · {sky}, später {low}°', 'up-to': '{t}° · {sky}, bis {high}°',
    },
    'en': {
        'night': 'Good night', 'morning': 'Good morning', 'day': 'Good afternoon', 'evening': 'Good evening',
        'birthday': 'Happy birthday, {name}!', 'birthday-anonymous': 'Happy birthday!',
        'new-years-eve': 'Happy New Year’s Eve!', 'new-years-day': 'Happy New Year!', 'easter': 'Happy Easter',
        'halloween': 'Trick or treat?', 'christmas': 'Merry Christmas', 'first-snow': 'It’s snowing!',
        'rain': 'Rain', 'snow': 'Snow', 'lasting': '{t}° · {wet}, still going',
        'until': '{t}° · {wet} until about {h}:00, then dry', 'from': '{t}° · {wet} from {h}:00',
        'clear-night': 'Clear', 'clear-day': 'Fair', 'cloudy': 'Cloudy',
        'later': '{t}° · {sky}, later {low}°', 'up-to': '{t}° · {sky}, up to {high}°',
    },
}
# Hamburger Schnack, an option for German: High German with Hamburg words, Low German only in the wishes.
# "Moin" all day long, as Hamburg says it.
TEXTS['de-hh'] = {
    **TEXTS['de'],
    'night': 'Moin', 'morning': 'Moin', 'day': 'Moin', 'evening': 'Moin',
    'birthday': 'Allens Gode, {name}!', 'birthday-anonymous': 'Allens Gode to’n Geburtsdag!',
    'new-years-eve': 'Kumm goot röver!', 'new-years-day': 'Prost Niejohr!', 'easter': 'Frohe Oostern',
    'christmas': 'Frohe Wiehnachten',
    'rain': 'Schietwetter', 'lasting': '{t}° · {wet}, und dat bleibt so', 'until': '{t}° · {wet} bis etwa {h} Uhr, denn is dröög',
    'clear-day': 'Kaiserwetter', 'cloudy': 'Grau in grau', 'fog': 'Waschküche',
}


@dataclass(frozen=True)
class Hour:
    """One hour of the forecast."""
    time: dt.datetime
    condition: str | None = None
    temperature: float | None = None
    gust: float | None = None
    wind: float | None = None


@dataclass(frozen=True)
class Weather:
    """Current weather and the hourly forecast, the first hour first."""
    condition: str | None
    temperature: float | None = None
    gust: float | None = None
    wind: float | None = None
    bearing: float | None = None  # where the wind comes from, degrees
    hours: tuple[Hour, ...] = ()


@dataclass(frozen=True)
class Inputs:
    now: dt.datetime                   # aware, local time zone
    sun_elevation: float               # degrees above the horizon
    weather: Weather
    warnings: tuple[str, ...] = ()     # headlines of the weather warnings in force
    events: tuple[str, ...] = ()       # titles of the calendar events going on now
    bin_day: bool = False              # a collection is due today
    water_level: float | None = None   # cm above gauge zero at Hamburg St. Pauli; None: no gauge or no answer
    ships: frozenset = frozenset()     # big ships in the harbour from AIS: 'cruise', 'container'


@dataclass(frozen=True)
class Settings:
    language: str = 'en'
    schnack: bool = False              # Hamburger Schnack, with German only
    keywords: dict = field(default_factory=lambda: dict(KEYWORDS))
    disabled: frozenset = frozenset()  # special days not to draw


@dataclass(frozen=True)
class Memory:
    """What update() needs from earlier updates; the integration stores it."""
    warning: str = 'none'
    warning_seen: dt.datetime | None = None
    snow_cover: bool = False
    first_snow: dt.date | None = None
    snowing_since: dt.datetime | None = None  # snowing at or below 1 degree
    falling_since: dt.datetime | None = None  # snowing at any temperature
    mild_since: dt.datetime | None = None     # above 3 degrees
    updated: dt.datetime | None = None
    tide: int | None = None                   # the step drawn last
    surge: bool = False                       # storm surge at the gauge
    water_seen: dt.datetime | None = None     # last answer from the gauge
    ice_drift: bool = False
    freezing_since: dt.datetime | None = None  # at or below 0 degrees without a break
    thawing_since: dt.datetime | None = None   # above 0 degrees without a break

    def to_dict(self):
        return {k: (v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v)
                for k, v in dataclasses.asdict(self).items()}

    @classmethod
    def from_dict(cls, data):
        """Restore from to_dict(); unknown or broken values fall back to the defaults."""
        out = {}
        for f in dataclasses.fields(cls):
            v = (data or {}).get(f.name)
            try:
                if f.name == 'first_snow':
                    v = dt.date.fromisoformat(v) if v else None
                elif f.name in DATETIMES:
                    v = dt.datetime.fromisoformat(v) if v else None
                elif f.name in ('snow_cover', 'surge', 'ice_drift'):
                    v = bool(v)
                elif f.name == 'tide':
                    v = v if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= TIDE_STEPS else None
                elif f.name == 'warning':
                    v = v if v in dict(WARNINGS) else 'none'
            except (TypeError, ValueError):
                v = None
            if v is not None:
                out[f.name] = v
        return cls(**out)


DATETIMES = ('warning_seen', 'snowing_since', 'falling_since', 'mild_since', 'updated', 'water_seen',
             'freezing_since', 'thawing_since')


@dataclass(frozen=True)
class State:
    key: str              # for the renderer
    scene: str            # <time of day>-<weather>
    time_of_day: str
    weather: str
    season: str
    wind: str
    direction: str
    gust: int
    moon: int             # 0 new, 4 full
    extremes: tuple
    tide: int | None      # 0 (mean low) .. 4 (mean high tide), None without a gauge
    ships: tuple          # big ships drawn
    warning: str
    event: str            # the special day drawn, or 'none'
    events: tuple         # all special days of the moment, most important first
    name: str             # birthday name, never drawn
    greeting: str         # by time of day
    wish: str             # for the special day, may be empty
    summary: str          # temperature and the next hours in a few words


def update(inputs, memory=Memory(), settings=Settings()):
    """The state for this moment and the memory for the next update."""
    now, w = inputs.now, inputs.weather
    memory = _remember_snow(memory, now, w)
    memory = _remember_ice(memory, now, w)
    memory = _remember_warning(memory, now, warning_kind(inputs.warnings))
    memory = _remember_water(memory, now, inputs.water_level)
    warning = memory.warning
    hours = w.hours[:12]
    upcoming = [w.condition] + [h.condition for h in hours[:3]]

    if any(c in SNOW for c in upcoming):
        weather = 'snow'
    elif any(c in RAIN for c in upcoming):
        weather = 'rain'
    elif w.condition in CLOUDS:
        weather = 'cloudy'
    else:
        weather = 'clear'
    e = inputs.sun_elevation
    tod = 'day' if e > 6 else 'dusk' if e > -6 else 'night'

    gusts = _known([w.gust] + [h.gust for h in hours[:3]])
    if gusts:
        gust = round(max(gusts))
        wind = 'storm' if gust >= GUSTS_STORM else 'windy' if gust >= GUSTS_WINDY else 'calm'
    else:
        gust = round(max(_known([w.wind] + [h.wind for h in hours[:3]]), default=0))
        wind = 'storm' if gust >= MEAN_STORM else 'windy' if gust >= MEAN_WINDY else 'calm'
    direction = 'east' if w.bearing is not None and w.bearing % 360 <= 180 else 'west'

    temps = _known([w.temperature] + [h.temperature for h in hours[:3]])
    extremes = set()
    if (temps and max(temps) >= HEAT) or warning == 'heat':
        extremes.add('heat')
    if (temps and min(temps) <= COLD) or warning == 'frost':
        extremes.add('cold')
    if memory.snow_cover:
        extremes.add('snow-cover')
    if memory.ice_drift:
        extremes.add('ice-drift')
    if w.condition == 'fog' or (hours and hours[0].condition == 'fog'):
        extremes.add('fog')
    if any(c in THUNDER for c in upcoming) or warning == 'thunder':
        extremes.add('thunder')
    if warning == 'storm-surge' or memory.surge:
        extremes.add('storm-surge')

    season = season_of(now.month)
    moon = moon_phase(now.date())
    found = special_days(now, e < -0.833, inputs.events, inputs.bin_day, memory.first_snow, settings)
    events = tuple(d for d, _ in found)
    event = events[0] if events else 'none'
    name = found[0][1] if event == 'birthday' else ''

    parts = [f'{tod}-{weather}', season, f'wind-{wind}' + ('' if wind == 'calm' else f'-{direction}')]
    if tod == 'night' and weather == 'clear':
        parts.append(f'moon-{moon}')
    if memory.tide is not None:
        parts.append(f'tide-{memory.tide}')
    parts += sorted(extremes)
    ships = tuple(sorted(k for k in inputs.ships if k in SHIPS))
    parts += [f'ship-{k}' for k in ships]
    if warning != 'none':
        parts.append(f'warning-{warning}')
    if event != 'none':
        parts.append(f'event-{event}')

    text = TEXTS['de-hh'] if settings.schnack and settings.language == 'de' else TEXTS.get(settings.language, TEXTS['en'])
    h = now.hour
    greeting = text['night' if h < 5 or h >= 22 else 'morning' if h < 11 else 'day' if h < 18 else 'evening']
    if event == 'birthday':
        wish = text['birthday'].format(name=name) if name else text['birthday-anonymous']
    else:
        wish = text.get(event, '') if event in ('new-years-eve', 'new-years-day', 'easter', 'halloween',
                                                 'christmas', 'first-snow') else ''
    state = State(key='.'.join(parts), scene=f'{tod}-{weather}', time_of_day=tod, weather=weather, season=season,
                  wind=wind, direction=direction, gust=gust, moon=moon, extremes=tuple(sorted(extremes)),
                  tide=memory.tide, ships=ships, warning=warning, event=event, events=events, name=name, greeting=greeting, wish=wish,
                  summary=_summary(text, now, w, hours, weather, tod))
    return state, memory


def _known(values):
    return [v for v in values if v is not None]


def _remember_snow(m, now, w):
    if m.updated is None or not dt.timedelta(0) <= now - m.updated <= GAP:
        m = dataclasses.replace(m, snowing_since=None, falling_since=None, mild_since=None, freezing_since=None,
                                thawing_since=None)
    m = dataclasses.replace(m, updated=now)
    falling = w.condition in SNOWFALL
    t = w.temperature
    snowing = falling and t is not None and t <= SNOW_COVER_ON[0]
    mild = t is not None and t > SNOW_COVER_OFF[0]
    m = dataclasses.replace(m, snowing_since=(m.snowing_since or now) if snowing else None,
                            falling_since=(m.falling_since or now) if falling else None,
                            mild_since=(m.mild_since or now) if mild else None)
    if m.snowing_since and now - m.snowing_since >= SNOW_COVER_ON[1]:
        m = dataclasses.replace(m, snow_cover=True)
    if m.mild_since and now - m.mild_since >= SNOW_COVER_OFF[1]:
        m = dataclasses.replace(m, snow_cover=False)
    if m.falling_since and now - m.falling_since >= FIRST_SNOW and now.month in FIRST_SNOW_MONTHS:
        winter = dt.date(now.year if now.month >= 8 else now.year - 1, 8, 1)
        if m.first_snow is None or m.first_snow < winter:
            m = dataclasses.replace(m, first_snow=now.date())
    return m


def tide_step(level, last=None):
    """The tide step for a water level; keeps the last step while the level is near its edge."""
    x = min(TIDE_STEPS, max(0, (level - MEAN_LOW_TIDE) / (MEAN_HIGH_TIDE - MEAN_LOW_TIDE) * TIDE_STEPS))
    if last is not None and abs(x - last) < .5 + TIDE_MARGIN:
        return last
    return math.floor(x + .5)


def _remember_water(m, now, level):
    if level is None:
        if m.water_seen and dt.timedelta(0) <= now - m.water_seen < WATER_HOLD:
            return m
        return dataclasses.replace(m, tide=None, surge=False, water_seen=None)
    surge = level >= STORM_SURGE or (m.surge and level >= STORM_SURGE_END)
    return dataclasses.replace(m, tide=tide_step(level, m.tide), surge=surge, water_seen=now)


def _remember_ice(m, now, w):
    t = w.temperature
    if t is None:
        return m
    freezing = t <= ICE_DRIFT_ON[0]
    m = dataclasses.replace(m, freezing_since=(m.freezing_since or now) if freezing else None,
                            thawing_since=None if freezing else (m.thawing_since or now))
    if m.freezing_since and now - m.freezing_since >= ICE_DRIFT_ON[1]:
        m = dataclasses.replace(m, ice_drift=True)
    if m.thawing_since and now - m.thawing_since >= ICE_DRIFT_OFF:
        m = dataclasses.replace(m, ice_drift=False)
    return m


def warning_kind(headlines):
    """The most severe kind among the warnings in force, or 'none'."""
    text = ' | '.join(headlines).upper()
    return next((kind for kind, pattern in WARNINGS if re.search(pattern, text)), 'none')


def _remember_warning(m, now, raw):
    if raw != 'none':
        return dataclasses.replace(m, warning=raw, warning_seen=now)
    if m.warning != 'none' and m.warning_seen and now - m.warning_seen < WARNING_HOLD:
        return m
    return dataclasses.replace(m, warning='none', warning_seen=None)


def season_of(month):
    """Meteorological seasons: winter is December to February."""
    return ('winter', 'spring', 'summer', 'autumn')[month % 12 // 3]


def moon_phase(day):
    """Moon phase in eighths for the day, 0 new, 4 full, as Home Assistant's moon sensor has it.

    The moon's age from its elongation (Meeus, Astronomical Algorithms, simplified
    terms), at midnight UTC, in 28ths of a lunation; quarters and full and new moon
    are one 28th wide, the phases between them six.
    """
    jd = day.toordinal() + 1721424.5
    t = (jd + (jd - 2382148) ** 2 / (41048480 * 86400) - 2451545.0) / 36525
    d = math.radians((297.85 + 445267.1115 * t - 0.00163 * t * t + t ** 3 / 545868) % 360)
    m = math.radians((357.53 + 35999.0503 * t) % 360)
    m1 = math.radians((134.96 + 477198.8676 * t + 0.008997 * t * t + t ** 3 / 69699) % 360)
    elong = math.degrees(d) + 6.29 * math.sin(m1) - 2.10 * math.sin(m) + 1.27 * math.sin(2 * d - m1) + 0.66 * math.sin(2 * d)
    age = (round(elong % 360) + 6.43) / 360 * 28 % 28
    for limit, phase in ((0.5, 0), (6.5, 1), (7.5, 2), (13.5, 3), (14.5, 4), (20.5, 5), (21.5, 6), (27.5, 7)):
        if age < limit:
            return phase
    return 0


def easter(year):
    """Easter Sunday (Gregorian calendar, anonymous algorithm)."""
    a, (b, c) = year % 19, divmod(year, 100)
    d, e = divmod(b, 4)
    g = (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return dt.date(year, month, day + 1)


def _sunday(year, month, n):
    """The n-th Sunday of the month; n = -1 for the last."""
    if n > 0:
        first = dt.date(year, month, 1)
        return first + dt.timedelta(days=(6 - first.weekday()) % 7 + 7 * (n - 1))
    last = dt.date(year + month // 12, month % 12 + 1, 1) - dt.timedelta(days=1)
    return last - dt.timedelta(days=(last.weekday() + 1) % 7)


def first_advent(year):
    christmas_eve = dt.date(year, 12, 24)
    return christmas_eve - dt.timedelta(days=(christmas_eve.weekday() + 1) % 7 + 21)


@functools.lru_cache(maxsize=4)
def holidays(year):
    """The special days of the year that follow from the calendar alone: {date: (day, ...)}.

    New Year's Eve and New Year's Day are missing: they depend on the hour.
    """
    e, advent, d = easter(year), first_advent(year), dt.date
    days = [
        (e - dt.timedelta(days=2), 'quiet'), (advent - dt.timedelta(days=14), 'quiet'),
        (advent - dt.timedelta(days=7), 'quiet'),
        (d(year, 1, 6), 'epiphany'), (d(year, 2, 14), 'valentines'),
        (e - dt.timedelta(days=48), 'carnival'), (e - dt.timedelta(days=47), 'carnival'),
        (e - dt.timedelta(days=1), 'easter'), (e, 'easter'), (e + dt.timedelta(days=1), 'easter'),
        (e + dt.timedelta(days=39), 'ascension'), (_sunday(year, 5, 2), 'mothers-day'),
        (_sunday(year, 3, -1), 'clock-change'), (_sunday(year, 10, -1), 'clock-change'),
        (d(year, 10, 31), 'halloween'), (d(year, 11, 11), 'st-martin'), (d(year, 12, 6), 'st-nicholas'),
        (d(year, 12, 24), 'christmas'), (d(year, 12, 25), 'christmas'), (d(year, 12, 26), 'christmas'),
    ]
    out = {}
    for day, name in days:
        out.setdefault(day, []).append(name)
    return {k: tuple(v) for k, v in out.items()}


def _keyword_pattern(keyword):
    return re.compile('^' + '(.*)'.join(re.escape(p) for p in keyword.split('*')) + r'(?!\w)', re.IGNORECASE)


def match_title(title, keywords):
    """(day, rest) for the first keyword the event title matches, or None; rest is what the keyword leaves."""
    for day, words in keywords.items():
        for word in words:
            m = _keyword_pattern(word).match(title.strip())
            if m:
                rest = ' '.join(g for g in m.groups() + (title.strip()[m.end():],) if g)
                return day, re.sub(r"[’']s$", '', rest.strip(' \t-–:,;')).strip()
    return None


def special_days(now, dark, titles=(), bin_day=False, first_snow=None, settings=Settings()):
    """All special days of the moment as (day, name), most important first; name only for birthdays."""
    today, h = now.date(), now.hour
    found = [(day, '') for day in holidays(today.year).get(today, ())]
    if (today.month, today.day) == (12, 31) and h >= 18 or (today.month, today.day) == (1, 1) and h < 2:
        found.append(('new-years-eve', ''))
    elif (today.month, today.day) == (1, 1) and h < 12:
        found.append(('new-years-day', ''))
    for title in titles:
        hit = match_title(title or '', settings.keywords)
        if hit:
            found.append((hit[0], hit[1] if hit[0] == 'birthday' else ''))
    if bin_day and BIN_HOURS[0] <= h < BIN_HOURS[1]:
        found.append(('bin-day', ''))
    if first_advent(today.year) <= today <= dt.date(today.year, 12, 23):
        found.append(('advent', ''))
    md = (today.month, today.day)
    if (6, 20) <= md <= (6, 22):
        found.append(('solstice', ''))
    if dark and ((8, 10) <= md <= (8, 14) or (12, 12) <= md <= (12, 15)):
        found.append(('shooting-stars', ''))
    if first_snow == today:
        found.append(('first-snow', ''))
    order = {day: i for i, day in enumerate(PRECEDENCE)}
    out, seen = [], set()
    for day, name in sorted(found, key=lambda f: order.get(f[0], len(order))):
        if day not in seen and day not in settings.disabled and day in order:
            seen.add(day)
            out.append((day, name))
    return out


def _summary(text, now, w, hours, weather, tod):
    t = round(w.temperature if w.temperature is not None else 0)
    conds = [h.condition for h in hours]

    def hour(i):
        return hours[i].time.astimezone(now.tzinfo).hour

    if weather in ('rain', 'snow'):
        wet = text[weather]
        if w.condition in WET or (conds and conds[0] in WET):
            dry = next((i for i, c in enumerate(conds) if c not in WET), None)
            if dry is None:
                return text['lasting'].format(t=t, wet=wet)
            return text['until'].format(t=t, wet=wet, h=hour(dry))
        start = next((i for i, c in enumerate(conds) if c in WET), None)
        if start is not None:
            return text['from'].format(t=t, wet=wet, h=hour(start))
    cloudy = weather == 'cloudy'
    grey = text['fog'] if 'fog' in text and w.condition == 'fog' else text['cloudy']   # only the Schnack has fog
    temps = [h.temperature for h in hours]
    if tod == 'night':
        low = round(min(_known(temps[:10]), default=t))
        return text['later'].format(t=t, sky=grey if cloudy else text['clear-night'], low=low)
    high = round(max(_known(temps[:8]), default=t))
    return text['up-to'].format(t=t, sky=grey if cloudy else text['clear-day'], high=high)
