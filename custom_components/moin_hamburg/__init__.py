"""Moin Hamburg: a living Hamburg skyline as dashboard background."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.storage import Store

from .const import (
    CONF_DEFAULT_THEME,
    DOMAIN,
    IMAGE_DIR,
    ISSUE_THEMES_NOT_LOADED,
    STORAGE_KEY,
    STORAGE_VERSION,
    THEME_FILE,
)
from .coordinator import MoinHamburgCoordinator
from .files import Files

PLATFORMS = [Platform.SENSOR, Platform.SWITCH]

type MoinHamburgConfigEntry = ConfigEntry[MoinHamburgCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MoinHamburgConfigEntry) -> bool:
    coordinator = MoinHamburgCoordinator(hass, entry)
    await coordinator.async_prepare()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.async_start())
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_options_updated))
    if entry.options.get(CONF_DEFAULT_THEME):
        await coordinator.async_set_default_theme()
    return True


async def _options_updated(hass: HomeAssistant, entry: MoinHamburgConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: MoinHamburgConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: MoinHamburgConfigEntry) -> None:
    """Take away images, theme file and memory; with the theme gone, the frontend falls back to its default."""
    files = Files(hass.config.path(*IMAGE_DIR), hass.config.path(*THEME_FILE))
    await hass.async_add_executor_job(files.remove)
    await Store(hass, STORAGE_VERSION, STORAGE_KEY).async_remove()
    ir.async_delete_issue(hass, DOMAIN, ISSUE_THEMES_NOT_LOADED)
    if hass.services.has_service('frontend', 'reload_themes'):
        await hass.services.async_call('frontend', 'reload_themes', blocking=True)
