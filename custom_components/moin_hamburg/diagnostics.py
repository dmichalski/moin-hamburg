"""Diagnostics: what Moin Hamburg saw and made of it, for bug reports.

Left out on purpose: the secret behind the image names and the image URLs (anyone with a URL could fetch the
picture without a login), calendar titles (they may name people; only the special day each one matched is kept),
the birthday name in the state and the wish, and the aisstream.io key.
"""
from __future__ import annotations

import dataclasses
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from . import MoinHamburgConfigEntry, state
from .const import CONF_AIS_KEY, DOMAIN, THEME
from .coordinator import FRONTEND_DEFAULT_THEME, FRONTEND_THEMES

TO_REDACT = {'name', 'wish'}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: MoinHamburgConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    integration = await async_get_integration(hass, DOMAIN)
    settings = coordinator.settings()
    inputs = coordinator.last_inputs
    out: dict[str, Any] = {
        'version': str(integration.version),
        'options': async_redact_data(dict(entry.options), {CONF_AIS_KEY}),
        'language': settings.language,
        'animated': coordinator.animated,
        'themes': {'loaded': THEME in hass.data.get(FRONTEND_THEMES, {}),
                   'default': hass.data.get(FRONTEND_DEFAULT_THEME)},
        'memory': coordinator.memory.to_dict(),
        'state': None,
        'inputs': None,
        'ais': coordinator.ais.diagnostics() if coordinator.ais else None,
    }
    if coordinator.data is not None:
        out['state'] = async_redact_data(dataclasses.asdict(coordinator.data.state), TO_REDACT)
    if inputs is not None:
        matched = [state.match_title(title, settings.keywords) for title in inputs.events]
        out['inputs'] = {
            'now': inputs.now.isoformat(),
            'sun_elevation': round(inputs.sun_elevation, 2),
            'weather': dataclasses.asdict(inputs.weather),
            'warnings': list(inputs.warnings),
            'events': [m[0] if m else None for m in matched],
            'bin_day': inputs.bin_day,
            'water_level': inputs.water_level,
            'ships': sorted(inputs.ships),
        }
    return out
