"""Fixtures for the Home Assistant tests (pytest-homeassistant-custom-component).

The renderer and state tests need none of this; they also run without pytest.
"""
import datetime as dt
from dataclasses import dataclass, field

import pytest

try:
    from homeassistant.core import SupportsResponse
except ImportError:  # plain Python without Home Assistant: only the standalone tests run
    SupportsResponse = None

THEME_KEY = 'frontend_themes'


@dataclass
class Fakes:
    """Stand-ins for weather forecasts, calendars and the frontend's theme services."""
    forecast: list = field(default_factory=list)
    calendars: dict = field(default_factory=dict)       # entity_id -> [(start, end, summary)]
    themes_loaded: bool = True                          # does the user's configuration load themes/?
    reloads: int = 0
    default_theme: list = field(default_factory=list)   # set_theme calls


@pytest.fixture
def fakes(hass, tmp_path):
    """A configuration folder of its own, Hamburg as home, and fake services."""
    hass.config.config_dir = str(tmp_path)
    hass.config.latitude, hass.config.longitude = 53.55, 9.99
    f = Fakes()

    def ids(call):
        e = call.data['entity_id']
        return [e] if isinstance(e, str) else list(e)

    async def get_forecasts(call):
        return {e: {'forecast': f.forecast} for e in ids(call)}

    async def get_events(call):
        start, end = call.data['start_date_time'], call.data['end_date_time']
        out = {}
        for e in ids(call):
            if e not in f.calendars:
                from homeassistant.exceptions import HomeAssistantError
                raise HomeAssistantError(f'{e} unavailable')
            out[e] = {'events': [{'summary': s, 'start': a.isoformat(), 'end': b.isoformat()}
                                 for a, b, s in f.calendars[e] if a < end and b > start]}
        return out

    async def reload_themes(call):
        f.reloads += 1
        theme = tmp_path / 'themes' / 'moin-hamburg.yaml'
        hass.data[THEME_KEY] = {'moin-hamburg': {}, 'moin-hamburg-still': {}} if f.themes_loaded and theme.exists() else {}

    async def set_theme(call):
        f.default_theme.append(dict(call.data))
        hass.data['frontend_default_theme'] = call.data['name']

    hass.services.async_register('weather', 'get_forecasts', get_forecasts, supports_response=SupportsResponse.ONLY)
    hass.services.async_register('calendar', 'get_events', get_events, supports_response=SupportsResponse.ONLY)
    hass.services.async_register('frontend', 'reload_themes', reload_themes)
    hass.services.async_register('frontend', 'set_theme', set_theme)
    hass.data[THEME_KEY] = {}
    hass.data['frontend_default_theme'] = 'default'
    return f


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request):
    if 'hass' in request.fixturenames:
        request.getfixturevalue('enable_custom_integrations')
    yield


def hourly(now, conditions, temperature=10, gust=20):
    start = now.replace(minute=0, second=0, microsecond=0)
    return [{'datetime': (start + dt.timedelta(hours=i)).isoformat(), 'condition': c, 'temperature': temperature,
             'wind_gust_speed': gust, 'wind_speed': gust / 2} for i, c in enumerate(conditions)]
