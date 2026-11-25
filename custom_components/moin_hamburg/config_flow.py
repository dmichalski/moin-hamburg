"""Setup and options: weather, warnings, calendars, water level, theme; in the options also keywords and days
left out."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from . import state
from .ais import async_check_key
from .const import (
    CONF_AIS_KEY,
    CONF_BIN_CALENDARS,
    CONF_DEFAULT_THEME,
    CONF_DISABLED_DAYS,
    CONF_EVENT_CALENDARS,
    CONF_KEYWORDS,
    CONF_SCHNACK,
    CONF_WARNINGS,
    CONF_WATER_LEVEL,
    CONF_WEATHER,
    DOMAIN,
    ST_PAULI_WATER_LEVEL,
)

try:
    import probatio as vol
except ImportError:  # Home Assistant before 2026.10
    import voluptuous as vol


def _entities(domain, multiple=False):
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domain, multiple=multiple))


def _schema():
    return vol.Schema({
        vol.Required(CONF_WEATHER): _entities('weather'),
        vol.Optional(CONF_WARNINGS): _entities(['binary_sensor', 'sensor'], multiple=True),
        vol.Optional(CONF_EVENT_CALENDARS): _entities('calendar', multiple=True),
        vol.Optional(CONF_BIN_CALENDARS): _entities('calendar', multiple=True),
        vol.Optional(CONF_WATER_LEVEL): _entities('sensor'),
        vol.Optional(CONF_DEFAULT_THEME): selector.BooleanSelector(),
    })


def _options_schema():
    keywords = vol.Schema({vol.Optional(day): selector.TextSelector() for day in state.KEYWORDS})
    return _schema().extend({
        vol.Required(CONF_KEYWORDS): section(keywords, {'collapsed': True}),
        vol.Optional(CONF_DISABLED_DAYS): selector.SelectSelector(selector.SelectSelectorConfig(
            options=list(state.PRECEDENCE), multiple=True, translation_key='day')),
        vol.Optional(CONF_SCHNACK): selector.BooleanSelector(),
        vol.Optional(CONF_AIS_KEY): selector.TextSelector(selector.TextSelectorConfig(
            type=selector.TextSelectorType.PASSWORD)),
    })


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    out = {CONF_WEATHER: user_input[CONF_WEATHER], CONF_WARNINGS: user_input.get(CONF_WARNINGS, []),
           CONF_EVENT_CALENDARS: user_input.get(CONF_EVENT_CALENDARS, []),
           CONF_BIN_CALENDARS: user_input.get(CONF_BIN_CALENDARS, []),
           CONF_DEFAULT_THEME: bool(user_input.get(CONF_DEFAULT_THEME, False))}
    if user_input.get(CONF_WATER_LEVEL):
        out[CONF_WATER_LEVEL] = user_input[CONF_WATER_LEVEL]
    if CONF_KEYWORDS in user_input:
        out[CONF_KEYWORDS] = {day: ', '.join(w.strip() for w in str(user_input[CONF_KEYWORDS].get(day) or '').split(',')
                                             if w.strip())
                              for day in state.KEYWORDS}
        out[CONF_DISABLED_DAYS] = list(user_input.get(CONF_DISABLED_DAYS, []))
        out[CONF_SCHNACK] = bool(user_input.get(CONF_SCHNACK, False))
        if str(user_input.get(CONF_AIS_KEY) or '').strip():
            out[CONF_AIS_KEY] = str(user_input[CONF_AIS_KEY]).strip()
    return out


def _errors(hass: HomeAssistant, user_input: dict[str, Any]) -> dict[str, str]:
    """The tide marks in state.py are those of Hamburg St. Pauli: another PEGELONLINE gauge would draw nonsense."""
    entity_id = user_input.get(CONF_WATER_LEVEL)
    entry = er.async_get(hass).async_get(entity_id) if entity_id else None
    if entry and entry.platform == 'pegel_online' and entry.unique_id != ST_PAULI_WATER_LEVEL:
        return {CONF_WATER_LEVEL: 'not_st_pauli'}
    return {}


class MoinHamburgConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = _errors(self.hass, user_input) if user_input is not None else {}
        if user_input is not None and not errors:
            return self.async_create_entry(title='Moin Hamburg', data={}, options=_clean(user_input))
        weather = sorted(self.hass.states.async_entity_ids('weather'))
        suggested = user_input or ({CONF_WEATHER: weather[0]} if weather else {})
        return self.async_show_form(step_id='user', data_schema=self.add_suggested_values_to_schema(_schema(), suggested),
                                    errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MoinHamburgOptionsFlow()


class MoinHamburgOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = _errors(self.hass, user_input) if user_input is not None else {}
        key = str((user_input or {}).get(CONF_AIS_KEY) or '').strip()
        if key and key != self.config_entry.options.get(CONF_AIS_KEY) and not errors:
            if problem := await async_check_key(self.hass, key):
                errors[CONF_AIS_KEY] = problem
        if user_input is not None and not errors:
            return self.async_create_entry(data=_clean(user_input))
        current = dict(user_input or self.config_entry.options)
        stored = current.get(CONF_KEYWORDS) or {}
        current[CONF_KEYWORDS] = {day: stored.get(day, ', '.join(words)) for day, words in state.KEYWORDS.items()}
        current.setdefault(CONF_DISABLED_DAYS, [])
        return self.async_show_form(step_id='init',
                                    data_schema=self.add_suggested_values_to_schema(_options_schema(), current),
                                    errors=errors)
