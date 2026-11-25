"""Sensors: the skyline state, greeting, weather summary and special day."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MoinHamburgConfigEntry
from .coordinator import Snapshot
from .entity import MoinHamburgEntity
from .state import PRECEDENCE

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class MoinHamburgSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Snapshot], str]
    attributes_fn: Callable[[Snapshot], dict[str, Any]] = lambda _: {}


def _skyline(d: Snapshot) -> dict[str, Any]:
    s = d.state
    return {'scene': s.scene, 'time_of_day': s.time_of_day, 'weather': s.weather, 'season': s.season,
            'wind': s.wind, 'wind_direction': s.direction, 'gust': s.gust, 'moon_phase': s.moon,
            'tide': s.tide,
            'extremes': list(s.extremes), 'warning': s.warning, 'special_day': s.event,
            'image': d.image, 'still_image': d.still}


SENSORS = (
    MoinHamburgSensorDescription(key='skyline', value_fn=lambda d: d.state.key, attributes_fn=_skyline),
    MoinHamburgSensorDescription(key='greeting', value_fn=lambda d: d.state.greeting,
                                 attributes_fn=lambda d: {'wish': d.state.wish}),
    MoinHamburgSensorDescription(key='summary', value_fn=lambda d: d.state.summary),
    MoinHamburgSensorDescription(
        key='special_day', device_class=SensorDeviceClass.ENUM, options=['none', *PRECEDENCE],
        value_fn=lambda d: d.state.event,
        attributes_fn=lambda d: {'all': list(d.state.events), 'name': d.state.name, 'wish': d.state.wish}),
)


async def async_setup_entry(hass: HomeAssistant, entry: MoinHamburgConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities(MoinHamburgSensor(entry.runtime_data, d) for d in SENSORS)


class MoinHamburgSensor(MoinHamburgEntity, SensorEntity):
    platform_domain = 'sensor'
    entity_description: MoinHamburgSensorDescription
    _unrecorded_attributes = frozenset({'image', 'still_image'})

    def __init__(self, coordinator, description: MoinHamburgSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.attributes_fn(self.coordinator.data)
