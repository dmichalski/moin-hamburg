"""Image: the picture of the moment, for picture cards, wall tablets without the theme and anything else that
shows an image entity.

It is the same SVG the theme moin-hamburg shows -- animated while the switch is on, otherwise the still one -- and
goes out through Home Assistant's image proxy, so it needs a login, unlike the files below www/.
"""
from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import MoinHamburgConfigEntry
from .coordinator import MoinHamburgCoordinator
from .entity import MoinHamburgEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: MoinHamburgConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([SkylineImage(entry.runtime_data, 'skyline')])


class SkylineImage(MoinHamburgEntity, ImageEntity):
    platform_domain = 'image'
    _attr_content_type = 'image/svg+xml'

    def __init__(self, coordinator: MoinHamburgCoordinator, key: str) -> None:
        MoinHamburgEntity.__init__(self, coordinator, key)
        ImageEntity.__init__(self, coordinator.hass)
        self._shown = self._url()
        self._attr_image_last_updated = dt_util.utcnow()

    def _url(self) -> str:
        data = self.coordinator.data
        return data.image if self.coordinator.animated else data.still

    @callback
    def _handle_coordinator_update(self) -> None:
        url = self._url()
        if url != self._shown:
            self._shown = url
            self._attr_image_last_updated = dt_util.utcnow()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        # '/moin_hamburg/<name>.svg?v=<hash>': the file of that name in the image folder
        name = self._url().split('?', 1)[0].rsplit('/', 1)[-1]
        path = self.coordinator.files.image_dir / name
        return await self.hass.async_add_executor_job(_read, path)


def _read(path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None
