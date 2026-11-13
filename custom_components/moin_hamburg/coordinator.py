"""Collects weather, sun, warnings and calendars, works out the state and keeps images and theme current."""
from __future__ import annotations

import dataclasses
import datetime as dt
import secrets
from dataclasses import dataclass
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.helpers.sun import get_astral_observer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import SpeedConverter, TemperatureConverter

from . import state
from .const import (
    CONF_BIN_CALENDARS,
    CONF_DISABLED_DAYS,
    CONF_EVENT_CALENDARS,
    CONF_KEYWORDS,
    CONF_WARNINGS,
    CONF_WEATHER,
    DOMAIN,
    IMAGE_DIR,
    ISSUE_THEMES_NOT_LOADED,
    LOGGER,
    STORAGE_KEY,
    STORAGE_VERSION,
    THEME,
    THEME_FILE,
    URL_PATH,
)
from .files import Files

try:
    from probatio import Invalid
except ImportError:  # Home Assistant before 2026.10
    from voluptuous import Invalid

GONE = (STATE_UNKNOWN, STATE_UNAVAILABLE, '')
CARDINAL = {d: i * 22.5 for i, d in enumerate(
    ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'))}
# Frontend internals, read only: which themes are loaded and which is the default.
FRONTEND_THEMES = 'frontend_themes'
FRONTEND_DEFAULT_THEME = 'frontend_default_theme'


@dataclass(frozen=True)
class Snapshot:
    state: state.State
    image: str
    still: str


class MoinHamburgCoordinator(DataUpdateCoordinator[Snapshot]):
    """Updates every quarter of an hour, and when the weather or a warning changes."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        super().__init__(hass, LOGGER, config_entry=entry, name=DOMAIN, update_interval=None,
                         request_refresh_debouncer=Debouncer(hass, LOGGER, cooldown=10, immediate=False))
        self.store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.files = Files(hass.config.path(*IMAGE_DIR), hass.config.path(*THEME_FILE))
        self.memory = state.Memory()
        self.animated = True

    @property
    def options(self) -> dict[str, Any]:
        return self.config_entry.options

    async def async_prepare(self) -> None:
        """Restore memory, create the image folder and serve it."""
        stored = await self.store.async_load() or {}
        self.memory = state.Memory.from_dict(stored.get('memory'))
        self.animated = bool(stored.get('animated', True))
        self.files.secret = stored.get('secret') or secrets.token_hex(16)
        if not stored.get('secret'):
            await self.store.async_save(self._stored())
        await self.hass.async_add_executor_job(self.files.prepare)
        flags = self.hass.data.setdefault(DOMAIN, {})
        if not flags.get('static_path') and self.hass.http is not None:
            from homeassistant.components.http import StaticPathConfig
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_PATH, str(self.files.image_dir), cache_headers=False)])
            flags['static_path'] = True

    def async_start(self) -> CALLBACK_TYPE:
        """Listen for the clock, the weather and the warnings; returns the function that stops listening."""
        async def refresh(_):
            await self.async_request_refresh()
        stops = [async_track_time_change(self.hass, refresh, minute=(0, 15, 30, 45), second=10),
                 async_track_state_change_event(
                     self.hass, [self.options[CONF_WEATHER], *self.options.get(CONF_WARNINGS, [])], refresh)]

        def stop() -> None:
            for unsubscribe in stops:
                unsubscribe()
        return stop

    async def async_set_animated(self, animated: bool) -> None:
        self.animated = animated
        self._save(urgent=True)
        await self.async_refresh()

    async def _async_update_data(self) -> Snapshot:
        now = dt_util.now()
        titles = await self._calendar_titles(self.options.get(CONF_EVENT_CALENDARS, []), now, now + dt.timedelta(minutes=1))
        day = dt_util.start_of_local_day(now)
        bin_day = bool(await self._calendar_titles(self.options.get(CONF_BIN_CALENDARS, []), day, day + dt.timedelta(days=1)))
        inputs = state.Inputs(now, self._sun_elevation(), await self._weather(now), tuple(self._warnings()),
                              tuple(titles), bin_day)
        result, memory = state.update(inputs, self.memory, self._settings())
        significant = dataclasses.replace(memory, updated=None) != dataclasses.replace(self.memory, updated=None)
        self.memory = memory
        self._save(urgent=significant)
        written = await self.hass.async_add_executor_job(self.files.write, result.key, result.scene, self.animated)
        if written.theme_changed:
            await self._reload_themes()
        return Snapshot(result, written.image, written.still)

    def _save(self, urgent: bool) -> None:
        # The snow clocks need the time of the last update only across short restarts: hourly is enough.
        self.store.async_delay_save(self._stored, 10 if urgent else 3600)

    def _stored(self) -> dict[str, Any]:
        return {'memory': self.memory.to_dict(), 'animated': self.animated, 'secret': self.files.secret}

    def _settings(self) -> state.Settings:
        keywords = dict(state.KEYWORDS)
        for day, text in (self.options.get(CONF_KEYWORDS) or {}).items():
            if day in keywords:
                keywords[day] = tuple(w.strip() for w in str(text or '').split(',') if w.strip())
        language = 'de' if (self.hass.config.language or '').lower().startswith('de') else 'en'
        return state.Settings(language=language, keywords=keywords,
                              disabled=frozenset(self.options.get(CONF_DISABLED_DAYS, [])))

    def _sun_elevation(self) -> float:
        from astral.sun import elevation  # Home Assistant's own dependency, as for sun.sun
        return elevation(get_astral_observer(self.hass), dt_util.utcnow())

    async def _weather(self, now: dt.datetime) -> state.Weather:
        entity_id = self.options[CONF_WEATHER]
        current = self.hass.states.get(entity_id)
        if current is None or current.state in GONE:
            raise UpdateFailed(translation_domain=DOMAIN, translation_key='weather_unavailable',
                               translation_placeholders={'entity': entity_id})
        a = current.attributes
        t_unit = a.get('temperature_unit') or UnitOfTemperature.CELSIUS
        w_unit = a.get('wind_speed_unit') or UnitOfSpeed.KILOMETERS_PER_HOUR

        def celsius(value):
            return _convert(value, TemperatureConverter, t_unit, UnitOfTemperature.CELSIUS)

        def kmh(value):
            return _convert(value, SpeedConverter, w_unit, UnitOfSpeed.KILOMETERS_PER_HOUR)

        hours = []
        try:
            response = await self.hass.services.async_call(
                'weather', 'get_forecasts', {'entity_id': entity_id, 'type': 'hourly'}, blocking=True,
                return_response=True)
            forecast = (response or {}).get(entity_id, {}).get('forecast') or []
        except (HomeAssistantError, Invalid) as err:
            LOGGER.debug('No hourly forecast from %s: %s', entity_id, err)
            forecast = []
        for f in forecast:
            time = dt_util.parse_datetime(str(f.get('datetime', '')))
            if time is None or time.tzinfo is None:
                continue
            if time + dt.timedelta(hours=1) <= now:
                continue  # hours already over
            hours.append(state.Hour(time, f.get('condition'), celsius(f.get('temperature')),
                                    kmh(f.get('wind_gust_speed')), kmh(f.get('wind_speed'))))
        return state.Weather(current.state, celsius(a.get('temperature')), kmh(a.get('wind_gust_speed')),
                             kmh(a.get('wind_speed')), _bearing(a.get('wind_bearing')), tuple(hours))

    def _warnings(self) -> list[str]:
        """Headlines of the warnings in force.

        NINA: the binary sensors (headline as attribute before 2026.11, else from
        the headline sensor of the same slot) or the headline sensors themselves.
        DWD: the warning level sensors, which list their warnings as attributes.
        """
        out = []
        registry = er.async_get(self.hass)
        for entity_id in self.options.get(CONF_WARNINGS, []):
            s = self.hass.states.get(entity_id)
            if s is None or s.state in GONE:
                continue
            a = s.attributes
            if 'warning_count' in a:
                for i in range(1, _int(a.get('warning_count')) + 1):
                    text = a.get(f'warning_{i}_headline') or a.get(f'warning_{i}_name')
                    if text:
                        out.append(str(text))
            elif s.domain == 'binary_sensor':
                if s.state != 'on':
                    continue
                text = a.get('headline')
                entry = registry.async_get(entity_id)
                if not text and entry and entry.platform == 'nina':
                    sibling = registry.async_get_entity_id('sensor', 'nina', f'{entry.unique_id}-headline')
                    sibling_state = self.hass.states.get(sibling) if sibling else None
                    text = sibling_state.state if sibling_state and sibling_state.state not in GONE else ''
                if text:
                    out.append(str(text))
            elif s.state.lower() not in ('off', 'none', '0'):
                out.append(s.state)
        return out

    async def _calendar_titles(self, entity_ids: list[str], start: dt.datetime, end: dt.datetime) -> list[str]:
        titles = []
        for entity_id in entity_ids:  # one by one: an unavailable calendar must not hide the others
            try:
                response = await self.hass.services.async_call(
                    'calendar', 'get_events',
                    {'entity_id': entity_id, 'start_date_time': start, 'end_date_time': end},
                    blocking=True, return_response=True)
            except (HomeAssistantError, Invalid) as err:
                LOGGER.debug('Calendar %s not read: %s', entity_id, err)
                continue
            titles += [str(e.get('summary') or '') for e in (response or {}).get(entity_id, {}).get('events', [])]
        return titles

    async def _reload_themes(self) -> None:
        if not self.hass.services.has_service('frontend', 'reload_themes'):
            return
        try:
            await self.hass.services.async_call('frontend', 'reload_themes', blocking=True)
        except HomeAssistantError as err:
            LOGGER.warning('Themes not reloaded: %s', err)
            return
        if THEME in self.hass.data.get(FRONTEND_THEMES, {}):
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_THEMES_NOT_LOADED)
        else:
            ir.async_create_issue(self.hass, DOMAIN, ISSUE_THEMES_NOT_LOADED, is_fixable=False,
                                  severity=ir.IssueSeverity.WARNING, translation_key=ISSUE_THEMES_NOT_LOADED)

    async def async_set_default_theme(self) -> None:
        """Make moin-hamburg the default theme, light and dark, unless it already is."""
        if THEME not in self.hass.data.get(FRONTEND_THEMES, {}):
            return
        if self.hass.data.get(FRONTEND_DEFAULT_THEME) == THEME:
            return
        await self.hass.services.async_call('frontend', 'set_theme', {'name': THEME, 'name_dark': THEME},
                                            blocking=True)


def _convert(value, converter, unit, target):
    if value is None:
        return None
    try:
        return converter.convert(float(value), unit, target)
    except (TypeError, ValueError, HomeAssistantError):
        return None


def _bearing(value):
    if isinstance(value, str) and value.strip().upper() in CARDINAL:
        return CARDINAL[value.strip().upper()]
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
