"""Switch: animated background on or off (the theme moin-hamburg shows the still image while off)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MoinHamburgConfigEntry
from .entity import MoinHamburgEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: MoinHamburgConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([AnimatedSwitch(entry.runtime_data, 'animated')])


class AnimatedSwitch(MoinHamburgEntity, SwitchEntity):
    platform_domain = 'switch'
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        return self.coordinator.animated

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_animated(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_animated(False)
