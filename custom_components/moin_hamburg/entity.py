"""Common base for the entities."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MoinHamburgCoordinator


class MoinHamburgEntity(CoordinatorEntity[MoinHamburgCoordinator]):
    _attr_has_entity_name = True
    platform_domain: str

    def __init__(self, coordinator: MoinHamburgCoordinator, key: str) -> None:
        super().__init__(coordinator)
        # The same entity IDs in every language, so dashboard examples work everywhere.
        self.entity_id = f'{self.platform_domain}.{DOMAIN}_{key}'
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f'{entry_id}-{key}'
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)}, name='Moin Hamburg',
                                            entry_type=DeviceEntryType.SERVICE)
