"""State logic: weather, warnings, special days, water level and memory -> state key and texts.

Runs with pytest or on its own: python3 tests/test_state.py
"""
import datetime as dt
import pathlib
import sys
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'custom_components' / 'moin_hamburg'), str(ROOT / 'tools')]

import golden  # noqa: E402
import render  # noqa: E402
import state  # noqa: E402
from state import Hour, Inputs, Memory, Settings, Weather  # noqa: E402

TZ = ZoneInfo('Europe/Berlin')
DE = Settings(language='de')


def at(text):
    return dt.datetime.fromisoformat(text).replace(tzinfo=TZ)


def forecast(now, conditions, temperature=12, gust=20):
    start = now.replace(minute=0, second=0, microsecond=0)
    return tuple(Hour(start + dt.timedelta(hours=i + 1), c, temperature, gust) for i, c in enumerate(conditions))


def run(now, *, elevation=30, condition='sunny', temperature=12, gust=20, wind=None, bearing=270, coming=None,
        warnings=(), events=(), bin_day=False, water=None, memory=Memory(), settings=DE, hours=None):
    now = at(now) if isinstance(now, str) else now
    if hours is None:
        hours = forecast(now, coming or [condition] * 12, temperature, gust)
    w = Weather(condition, temperature, gust, wind, bearing, hours)
    return state.update(Inputs(now, elevation, w, tuple(warnings), tuple(events), bin_day, water), memory, settings)


def event(now, **kw):
    return run(now, **kw)[0].event


# -- picture: scene, wind, extremes, key ---------------------------------------------------------------

def test_time_of_day_by_sun_elevation():
    assert [run('2026-11-10 12:00', elevation=e)[0].time_of_day for e in (6.1, 6, -5.9, -6)] == \
        ['day', 'dusk', 'dusk', 'night']


def test_weather_of_the_next_three_hours():
    def weather(now, coming):
        return run('2026-11-10 12:00', condition=now, coming=coming)[0].weather
    assert weather('sunny', ['sunny'] * 12) == 'clear'
    assert weather('partlycloudy', ['sunny'] * 12) == 'clear'
    assert weather('cloudy', ['sunny'] * 12) == 'cloudy'
    assert weather('fog', ['sunny'] * 12) == 'cloudy'
    assert weather('sunny', ['sunny', 'sunny', 'rainy'] + ['sunny'] * 9) == 'rain'
    assert weather('sunny', ['sunny'] * 3 + ['pouring'] * 9) == 'clear'      # hour four is too far
    assert weather('rainy', ['sunny', 'snowy-rainy'] + ['rainy'] * 10) == 'snow'  # snow beats rain
    assert weather('cloudy', ['hail'] + ['sunny'] * 11) == 'snow'


def test_wind_level_and_direction():
    def wind(**kw):
        s = run('2026-11-10 12:00', **kw)[0]
        return s.wind, s.direction, s.gust
    assert wind(gust=39.4) == ('calm', 'west', 39)
    assert wind(gust=40) == ('windy', 'west', 40)
    assert wind(gust=75, bearing=90) == ('storm', 'east', 75)
    assert wind(gust=20, bearing=180)[1] == 'east'
    assert wind(gust=20, bearing=181)[1] == 'west'
    assert wind(gust=20, bearing=None)[1] == 'west'
    now = at('2026-11-10 12:00')
    gusty_later = forecast(now, ['cloudy'] * 12, gust=20)[:2] + (Hour(now + dt.timedelta(hours=3), 'cloudy', 12, 80),)
    assert wind(hours=gusty_later)[0] == 'storm'
    # without gusts from the weather service: the mean wind, with lower thresholds
    no_gusts = tuple(Hour(h.time, h.condition, h.temperature, None, 30) for h in forecast(now, ['cloudy'] * 12))
    assert wind(gust=None, wind=20, hours=no_gusts) == ('windy', 'west', 30)


def test_extremes():
    def extremes(**kw):
        return run('2026-07-10 12:00', **kw)[0].extremes
    assert extremes(temperature=29.9) == ()
    assert extremes(temperature=30) == ('heat',)
    assert extremes(temperature=-8) == ('cold',)
    assert extremes(condition='fog') == ('fog',)
    assert extremes(coming=['cloudy', 'lightning-rainy'] + ['cloudy'] * 10) == ('thunder',)
    assert extremes(warnings=['Amtliche WARNUNG vor HITZE']) == ('heat',)
    assert extremes(warnings=['Amtliche WARNUNG vor STRENGEM FROST']) == ('cold',)
    assert extremes(warnings=['Amtliche WARNUNG vor STURMFLUT']) == ('storm-surge',)
    assert extremes(memory=Memory(snow_cover=True), temperature=0) == ('snow-cover',)


def test_key():
    s, _ = run('2026-11-11 20:00', elevation=-30, gust=10)
    assert s.key == f'night-clear.autumn.wind-calm.moon-{s.moon}.event-st-martin'
    s, _ = run('2026-11-10 12:00', condition='cloudy', gust=50, bearing=100, temperature=-9,
               warnings=['Amtliche WARNUNG vor STURMBÖEN'])
    assert s.key == 'day-cloudy.autumn.wind-windy-east.cold.warning-storm-gusts'
    s, _ = run('2026-07-10 12:00', condition='fog', coming=['lightning'] * 12, temperature=31)
    assert s.key == 'day-rain.summer.wind-calm.fog.heat.thunder'  # extremes in alphabetical order


def test_moon_only_at_clear_night():
    assert '.moon-' in run('2026-11-10 23:00', elevation=-40)[0].key
    assert '.moon-' not in run('2026-11-10 23:00', elevation=-40, condition='cloudy')[0].key
    assert '.moon-' not in run('2026-11-10 17:00', elevation=-3)[0].key


def test_every_key_draws():
    """Whatever update() says, the renderer must accept; special days and warnings are the ones it knows."""
    assert set(state.PRECEDENCE) == set(golden.EVENTS)
    assert {kind for kind, _ in state.WARNINGS} == set(golden.WARNINGS)
    weathers = [{}, {'condition': 'cloudy', 'gust': 50, 'bearing': 90}, {'condition': 'rainy', 'coming': ['lightning'] * 12},
                {'condition': 'snowy', 'gust': 90, 'temperature': -10, 'warnings': ['ORKAN', 'STURMFLUT'],
                 'memory': Memory(snow_cover=True)}, {'condition': 'fog', 'temperature': 33, 'warnings': ['SCHNEE']},
                {'water': 300}, {'water': 560, 'condition': 'rainy'}, {'water': 950, 'gust': 80}]
    t, n, days = at('2026-01-01 00:00'), 0, set()
    while t.year == 2026:
        s, _ = run(t, elevation=(t.hour - 12) * 4, events=['Geburtstag Kim', 'Dom', 'Herbstferien'][n % 4:n % 4 + 1],
                   bin_day=True, **weathers[n % len(weathers)])
        render.parse_key(s.key)
        days.update(s.events)
        t, n = t + dt.timedelta(hours=5), n + 1
    assert days == set(state.PRECEDENCE) - {'first-snow', 'cherry-blossom', 'pride', 'blue-port', 'harbour-birthday'}


# -- water level: tide and storm surge at Hamburg St. Pauli ---------------------------------------------

def test_tide_steps():
    steps = [state.tide_step(level) for level in (192, 347, 395, 438, 529, 620, 667, 711, 1065)]
    assert steps == [0, 0, 1, 1, 2, 3, 4, 4, 4]
    from render.palette import TIDE_STEPS
    assert state.TIDE_STEPS == TIDE_STEPS


def test_tide_keeps_its_step_near_the_edge():
    step = 91  # cm per step
    assert state.tide_step(347 + 1.6 * step, last=1) == 1 and state.tide_step(347 + 1.7 * step, last=1) == 2
    assert state.tide_step(347 + 1.4 * step, last=2) == 2 and state.tide_step(347 + 1.3 * step, last=2) == 1
    assert state.tide_step(1065, last=4) == 4 and state.tide_step(100, last=0) == 0


def test_tide_in_the_key():
    s, m = run('2026-11-25 12:00', condition='cloudy', water=400)
    assert s.key == 'day-cloudy.autumn.wind-calm.tide-1' and s.tide == 1 and m.tide == 1
    s, _ = run('2026-11-25 23:00', elevation=-30, water=711)
    assert s.key.startswith('night-clear.autumn.wind-calm.moon-') and s.key.endswith('.tide-4')
    s, m = run('2026-11-25 12:00')
    assert 'tide' not in s.key and s.tide is None and m.tide is None   # no gauge, no tide


def test_storm_surge_from_the_gauge():
    s, m = run('2027-01-12 03:00', water=860)
    assert 'storm-surge' not in s.extremes and s.tide == 4
    s, m = run('2027-01-12 03:15', water=861, memory=m)
    assert s.extremes == ('storm-surge',) and s.key == 'day-clear.winter.wind-calm.tide-4.storm-surge'
    s, m = run('2027-01-12 03:30', water=852, memory=m)
    assert 'storm-surge' in s.extremes                                  # not over until 10 cm below
    s, m = run('2027-01-12 03:45', water=850, memory=m)
    assert 'storm-surge' not in s.extremes and not m.surge
    s, _ = run('2027-01-12 03:45', water=500, warnings=['Amtliche WARNUNG vor STURMFLUT'])
    assert 'storm-surge' in s.extremes and s.warning == 'storm-surge'   # a warning still counts on its own


def test_gauge_without_answer_keeps_its_picture_for_an_hour():
    s, m = run('2026-11-25 12:00', water=900)
    s, m = run('2026-11-25 12:59', memory=m)
    assert s.tide == 4 and 'storm-surge' in s.extremes
    s, m = run('2026-11-25 13:00', memory=m)
    assert s.tide is None and not s.extremes and m.water_seen is None


# -- warnings ------------------------------------------------------------------------------------------

def test_warning_kinds():
    k = state.warning_kind
    assert k([]) == 'none'
    assert k(['Amtliche WARNUNG vor STURMBÖEN']) == 'storm-gusts'
    assert k(['Amtliche UNWETTERWARNUNG vor ORKANBÖEN']) == 'hurricane'
    assert k(['Amtliche WARNUNG vor ORKANARTIGEN BÖEN']) == 'hurricane'
    assert k(['Amtliche WARNUNG vor STURMFLUT']) == 'storm-surge'
    assert k(['Amtliche WARNUNG vor STARKEM GEWITTER']) == 'thunder'
    assert k(['Amtliche WARNUNG vor STRENGEM FROST']) == 'frost'
    assert k(['Amtliche WARNUNG vor FROST']) == 'none'  # plain frost is just winter
    assert k(['Amtliche WARNUNG vor SCHNEEFALL']) == 'snow'
    assert k(['Amtliche WARNUNG vor GLÄTTE']) == 'none'
    assert k(['Official WARNING of HEAVY THUNDERSTORMS']) == 'thunder'  # not storm gusts
    assert k(['Official WARNING of GALE-FORCE GUSTS']) == 'storm-gusts'
    assert k(['Amtliche WARNUNG vor GEWITTER', 'Amtliche WARNUNG vor STURMBÖEN']) == 'storm-gusts'


def test_warning_is_held_for_30_minutes():
    gusts = ['Amtliche WARNUNG vor STURMBÖEN']
    s, m = run('2026-10-07 10:00', warnings=gusts)
    assert s.warning == 'storm-gusts'
    s, m = run('2026-10-07 10:20', memory=m)         # the feed is empty between two issues
    assert s.warning == 'storm-gusts'
    s, m = run('2026-10-07 10:25', memory=m, warnings=gusts)
    s, m = run('2026-10-07 10:54', memory=m)
    assert s.warning == 'storm-gusts'
    s, m = run('2026-10-07 10:55', memory=m)
    assert s.warning == 'none' and m.warning_seen is None


def test_warning_while_calm():
    """The case of 2026-10-07: a storm warning, but still air at the time."""
    s, _ = run('2026-10-07 10:00', gust=12, warnings=['Amtliche WARNUNG vor STURMBÖEN'])
    assert 'wind-calm' in s.key and s.key.endswith('warning-storm-gusts')


# -- special days --------------------------------------------------------------------------------------

def test_new_year_by_the_hour():
    assert [event(t) for t in ('2026-12-31 17:59', '2026-12-31 18:00', '2027-01-01 01:59', '2027-01-01 02:00',
                               '2027-01-01 11:59', '2027-01-01 12:00')] == \
        ['none', 'new-years-eve', 'new-years-eve', 'new-years-day', 'new-years-day', 'none']


def test_easter():
    assert [state.easter(y) for y in (2024, 2025, 2026, 2027, 2028, 2038, 2285)] == [
        dt.date(2024, 3, 31), dt.date(2025, 4, 20), dt.date(2026, 4, 5), dt.date(2027, 3, 28),
        dt.date(2028, 4, 16), dt.date(2038, 4, 25), dt.date(2285, 3, 22)]


def test_holidays_as_in_the_german_holiday_calendar():
    """The days the legacy setup read from Google's German holiday calendar, August 2026 to 2027."""
    d = dt.date
    expected = {
        d(2026, 10, 25): ('clock-change',), d(2026, 10, 31): ('halloween',), d(2026, 11, 11): ('st-martin',),
        d(2026, 11, 15): ('quiet',), d(2026, 11, 22): ('quiet',), d(2026, 12, 6): ('st-nicholas',),
        d(2026, 12, 24): ('christmas',), d(2026, 12, 25): ('christmas',), d(2026, 12, 26): ('christmas',),
        d(2027, 1, 6): ('epiphany',), d(2027, 2, 8): ('carnival',), d(2027, 2, 9): ('carnival',),
        d(2027, 2, 14): ('valentines',), d(2027, 3, 26): ('quiet',), d(2027, 3, 27): ('easter',),
        d(2027, 3, 28): ('clock-change', 'easter'), d(2027, 3, 29): ('easter',), d(2027, 5, 6): ('ascension',),
        d(2027, 5, 9): ('mothers-day',), d(2027, 10, 31): ('clock-change', 'halloween'),
        d(2027, 11, 11): ('st-martin',), d(2027, 11, 14): ('quiet',), d(2027, 11, 21): ('quiet',),
        d(2027, 12, 6): ('st-nicholas',), d(2027, 12, 24): ('christmas',), d(2027, 12, 25): ('christmas',),
        d(2027, 12, 26): ('christmas',),
    }
    got = {day: tuple(sorted(v)) for y in (2026, 2027) for day, v in state.holidays(y).items()
           if day >= d(2026, 8, 1)}
    assert got == expected
    assert state.first_advent(2026) == d(2026, 11, 29) and state.first_advent(2027) == d(2027, 11, 28)
    assert state.first_advent(2023) == d(2023, 12, 3)  # Christmas Eve on a Sunday


def test_easter_and_halloween_beat_the_clock_change():
    assert event('2027-03-28 12:00') == 'easter'
    assert event('2027-10-31 12:00') == 'halloween'
    assert event('2026-10-25 12:00') == 'clock-change'


def test_precedence():
    # birthday before a holiday before a period
    s, _ = run('2026-12-24 12:00', events=['Geburtstag Kim'])
    assert (s.event, s.name, s.wish, s.events) == ('birthday', 'Kim', 'Alles Gute, Kim!', ('birthday', 'christmas'))
    s, _ = run('2026-12-06 12:00', events=['Dom: Winterdom'])
    assert s.events == ('st-nicholas', 'dom', 'advent')
    assert event('2026-12-10 12:00', events=['Dom: Winterdom']) == 'dom'
    assert event('2026-12-10 12:00') == 'advent'
    # a quiet day before everything, and then nobody is wished anything
    s, _ = run('2026-11-22 12:00', events=['Geburtstag Kim', 'Dom: Winterdom'])
    assert (s.event, s.name, s.wish, s.events) == ('quiet', '', '', ('quiet', 'birthday', 'dom'))
    assert event('2027-03-26 12:00') == 'quiet'


def test_bin_day_only_from_6_to_10():
    assert [event(t, bin_day=True) for t in ('2026-10-16 05:59', '2026-10-16 06:00', '2026-10-16 09:59',
                                             '2026-10-16 10:00')] == ['none', 'bin-day', 'bin-day', 'none']
    assert event('2026-10-16 08:00', bin_day=True, events=['Herbstferien']) == 'school-holidays'


def test_days_by_date():
    assert [event(t) for t in ('2026-06-19 12:00', '2026-06-20 12:00', '2026-06-22 23:00', '2026-06-23 00:00')] == \
        ['none', 'solstice', 'solstice', 'none']
    assert [event(t) for t in ('2026-11-28 12:00', '2026-11-29 00:00', '2026-12-23 23:59', '2026-12-27 12:00')] == \
        ['none', 'advent', 'advent', 'none']
    # shooting stars only in the dark
    assert event('2026-08-12 23:00', elevation=-20) == 'shooting-stars'
    assert event('2026-08-12 21:00', elevation=-0.5) == 'none'
    assert event('2026-12-13 12:00', elevation=10) == 'advent'
    assert event('2026-12-13 23:00', elevation=-50) == 'shooting-stars'
    assert event('2026-08-15 23:00', elevation=-20) == 'none'


def test_calendar_keywords():
    m = state.match_title
    k = state.KEYWORDS
    assert m('Hafengeburtstag', k) == ('harbour-birthday', '')
    assert m('Dom: Frühlingsdom', k) == ('dom', 'Frühlingsdom')
    assert m('Hamburger Dom', k)[0] == 'dom'
    assert m('Domführung', k) is None
    assert m('csd hamburg', k)[0] == 'pride'
    assert m('Blue Port 2027', k)[0] == 'blue-port'
    assert m('Herbstferien', k)[0] == 'school-holidays'
    assert m('Ferien', k)[0] == 'school-holidays'
    assert m('Ferienwohnung buchen', k) is None
    assert m('Geburtstag Kim', k) == ('birthday', 'Kim')
    assert m('Geburtstagsfeier planen', k) is None
    assert m("Sam's birthday", k) == ('birthday', 'Sam')
    assert m('Birthday: Kim', k) == ('birthday', 'Kim')
    assert m('Geburtstag', k) == ('birthday', '')
    assert m('Zahnarzt', k) is None
    s, _ = run('2026-05-10 12:00', events=['Geburtstag'])
    assert s.wish == 'Alles Gute zum Geburtstag!'


def test_settings():
    own = Settings(language='de', keywords={'dom': ('Jahrmarkt',)}, disabled=frozenset({'advent'}))
    assert event('2026-12-10 12:00', settings=own) == 'none'
    assert event('2026-12-10 12:00', events=['Jahrmarkt'], settings=own) == 'dom'
    assert event('2026-12-10 12:00', events=['Dom'], settings=own) == 'none'


# -- snow and memory -----------------------------------------------------------------------------------

def steps(start, end, memory=Memory(), **kw):
    """An update every 15 minutes from start to end, as the integration does; the last state and memory."""
    t, end, result = at(start), at(end), None
    while t <= end:
        result, memory = run(t, memory=memory, **kw)
        t += dt.timedelta(minutes=15)
    return result, memory


def test_snow_cover():
    snowing = {'condition': 'snowy', 'temperature': 1}
    _, m = steps('2026-12-02 07:00', '2026-12-02 08:45', **snowing)
    assert not m.snow_cover
    _, m = steps('2026-12-02 09:00', '2026-12-02 09:00', m, **snowing)
    assert m.snow_cover
    _, m = steps('2026-12-02 09:15', '2026-12-02 15:00', m, condition='cloudy', temperature=3.5)
    assert m.snow_cover
    s, m = steps('2026-12-02 15:15', '2026-12-02 15:15', m, condition='cloudy', temperature=3.5)
    assert not m.snow_cover and 'snow-cover' not in s.extremes
    # an interruption starts the count again
    _, m = steps('2026-12-02 07:00', '2026-12-02 07:45', **snowing)
    _, m = steps('2026-12-02 08:00', '2026-12-02 08:00', m, condition='cloudy', temperature=0)
    _, m = steps('2026-12-02 08:15', '2026-12-02 10:00', m, **snowing)
    assert not m.snow_cover
    s, m = steps('2026-12-02 10:15', '2026-12-02 10:15', m, **snowing)
    assert m.snow_cover and 'snow-cover' in s.extremes
    # so does a gap in the updates: Home Assistant was down, nobody saw what the weather did
    _, m = steps('2026-12-02 07:00', '2026-12-02 08:00', **snowing)
    _, m = steps('2026-12-02 11:00', '2026-12-02 12:45', m, **snowing)
    assert not m.snow_cover
    _, m = steps('2026-12-02 13:00', '2026-12-02 13:00', m, **snowing)
    assert m.snow_cover
    # too warm: it snows, but nothing settles
    _, m = steps('2026-12-02 07:00', '2026-12-02 10:00', condition='snowy', temperature=2)
    assert not m.snow_cover


def test_first_snow():
    snowing = {'condition': 'snowy', 'temperature': 2}
    s, m = run('2026-11-10 07:00', **snowing)
    s, m = run('2026-11-10 07:14', memory=m, **snowing)
    assert m.first_snow is None and s.event == 'none'
    s, m = run('2026-11-10 07:15', memory=m, **snowing)
    assert m.first_snow == dt.date(2026, 11, 10) and (s.event, s.wish) == ('first-snow', 'Es schneit!')
    s, _ = run('2026-11-11 08:00', memory=m)
    assert s.event == 'st-martin' and 'first-snow' not in s.events
    # only once a winter
    _, m2 = steps('2027-01-20 07:00', '2027-01-20 08:00', m, **snowing)
    assert m2.first_snow == dt.date(2026, 11, 10)
    # the next winter starts on 1 August, and snow in September does not count
    _, m3 = steps('2027-09-20 07:00', '2027-09-20 08:00', m, **snowing)
    assert m3.first_snow == dt.date(2026, 11, 10)
    _, m3 = steps('2027-10-20 07:00', '2027-10-20 07:15', m, **snowing)
    assert m3.first_snow == dt.date(2027, 10, 20)


def test_memory_round_trip():
    _, m = run('2026-12-02 07:00', condition='snowy', temperature=0, warnings=['ORKAN'],
               memory=Memory(snow_cover=True, first_snow=dt.date(2026, 11, 10)))
    assert Memory.from_dict(m.to_dict()) == m
    assert Memory.from_dict(None) == Memory()
    assert Memory.from_dict({'warning': 'tornado', 'first_snow': 'gestern', 'warning_seen': 5, 'x': 1}) == Memory()
    _, m = run('2027-01-12 03:00', water=900)
    assert m.tide == 4 and m.surge and Memory.from_dict(m.to_dict()) == m
    assert Memory.from_dict({'tide': 7}) == Memory() and Memory.from_dict({'tide': True}) == Memory()


# -- texts ---------------------------------------------------------------------------------------------

def test_greeting_by_hour():
    hours = ('04:59', '05:00', '10:59', '11:00', '17:59', '18:00', '21:59', '22:00')
    assert [run(f'2026-11-10 {h}')[0].greeting for h in hours] == [
        'Gute Nacht', 'Guten Morgen', 'Guten Morgen', 'Guten Tag', 'Guten Tag', 'Guten Abend', 'Guten Abend',
        'Gute Nacht']
    assert run('2026-11-10 08:00', settings=Settings())[0].greeting == 'Good morning'


def test_wishes():
    assert run('2026-12-31 20:00')[0].wish == 'Guten Rutsch!'
    assert run('2027-01-01 09:00')[0].wish == 'Frohes neues Jahr!'
    assert run('2026-12-25 09:00', settings=Settings())[0].wish == 'Merry Christmas'
    assert run('2026-11-11 09:00')[0].wish == ''


def test_summary():
    def summary(conditions, now_condition, temps=None, elevation=30, settings=DE):
        now = at('2026-11-10 12:20')
        hours = tuple(Hour(now.replace(minute=0) + dt.timedelta(hours=i + 1), c, (temps or [12] * 12)[i], 10)
                      for i, c in enumerate(conditions))
        return run(now, condition=now_condition, temperature=11.6, hours=hours, elevation=elevation,
                   settings=settings)[0].summary
    assert summary(['rainy', 'rainy', 'cloudy'] + ['cloudy'] * 9, 'rainy') == '12° · Regen bis etwa 15 Uhr, danach trocken'
    assert summary(['rainy'] * 12, 'pouring') == '12° · Regen, hält noch an'
    assert summary(['cloudy', 'snowy'] + ['cloudy'] * 10, 'cloudy') == '12° · ab 14 Uhr Schnee'
    assert summary(['cloudy', 'snowy'] + ['cloudy'] * 10, 'cloudy', settings=Settings()) == '12° · Snow from 14:00'
    temps = [12, 14, 16, 9, 9, 9, 9, 18, 30, 2, 1, 0]
    assert summary(['sunny'] * 12, 'sunny', temps) == '12° · Heiter, bis 18°'
    assert summary(['cloudy'] * 12, 'cloudy', temps, elevation=-20) == '12° · Bewölkt, später 2°'
    assert summary(['sunny'] * 12, 'clear-night', temps, elevation=-20, settings=Settings()) == '12° · Clear, later 2°'


# -- moon ----------------------------------------------------------------------------------------------

def test_moon_as_home_assistant_saw_it():
    """sensor.moon_phase on a live Home Assistant, 1 to 10 November 2026."""
    seen = {1: 6, 2: 7, 8: 7, 9: 0, 10: 1}
    assert {d: state.moon_phase(dt.date(2026, 11, d)) for d in seen} == seen


def test_moon_matches_astral():
    """Same phase as Home Assistant's moon sensor (astral) for every day of 1990-2060; needs astral installed."""
    try:
        from astral import moon
    except ImportError:
        return
    limits = ((0.5, 0), (6.5, 1), (7.5, 2), (13.5, 3), (14.5, 4), (20.5, 5), (21.5, 6), (27.5, 7), (99, 0))
    day, wrong = dt.date(1990, 1, 1), []
    while day.year < 2061:
        expected = next(p for limit, p in limits if moon.phase(day) < limit)
        if state.moon_phase(day) != expected:
            wrong.append(day)
        day += dt.timedelta(days=1)
    assert not wrong, f'{len(wrong)} days differ, first {wrong[:3]}'


def test_season():
    assert [state.season_of(m) for m in range(1, 13)] == ['winter'] * 2 + ['spring'] * 3 + ['summer'] * 3 + \
        ['autumn'] * 3 + ['winter']


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
