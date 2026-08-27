"""Sensor platform for PiggyTask — per-child sensors plus a family-total sensor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import ChildTaskCounts, TaskCountsResult
from .const import DOMAIN
from .coordinator import PiggyTaskCoordinator
from .entity import child_device_info, child_entity_adder, family_device_info


@dataclass(frozen=True, kw_only=True)
class PiggyTaskSensorDescription(SensorEntityDescription):
    """Describes one of the per-child count sensors."""

    value_fn: Callable[[ChildTaskCounts], int]


@dataclass(frozen=True, kw_only=True)
class PiggyTaskFamilySensorDescription(SensorEntityDescription):
    """Describes one of the family-total sensors (aggregated across all children)."""

    value_fn: Callable[[TaskCountsResult], int]


SENSOR_DESCRIPTIONS: tuple[PiggyTaskSensorDescription, ...] = (
    PiggyTaskSensorDescription(
        key="open_tasks",
        translation_key="open_tasks",
        icon="mdi:clipboard-list-outline",
        native_unit_of_measurement="tasks",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda child: child.open_tasks,
    ),
    PiggyTaskSensorDescription(
        key="overdue_tasks",
        translation_key="overdue_tasks",
        icon="mdi:clipboard-alert-outline",
        native_unit_of_measurement="tasks",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda child: child.overdue_tasks,
    ),
    PiggyTaskSensorDescription(
        key="due_today",
        translation_key="due_today",
        icon="mdi:clipboard-clock-outline",
        native_unit_of_measurement="tasks",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda child: child.due_today,
    ),
    PiggyTaskSensorDescription(
        key="coin_balance",
        translation_key="coin_balance",
        icon="mdi:cash-multiple",
        native_unit_of_measurement="coins",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda child: child.coin_balance,
    ),
    PiggyTaskSensorDescription(
        key="xp_balance",
        translation_key="xp_balance",
        icon="mdi:star-four-points-outline",
        native_unit_of_measurement="xp",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda child: child.xp_balance,
    ),
    PiggyTaskSensorDescription(
        key="level",
        translation_key="level",
        icon="mdi:trophy-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda child: child.level,
    ),
)

FAMILY_SENSOR_DESCRIPTIONS: tuple[PiggyTaskFamilySensorDescription, ...] = (
    PiggyTaskFamilySensorDescription(
        key="family_open_tasks",
        translation_key="family_open_tasks",
        icon="mdi:clipboard-list-outline",
        native_unit_of_measurement="tasks",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sum(child.open_tasks for child in data.children),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up PiggyTask sensors, adding entities as new children appear."""
    coordinator: PiggyTaskCoordinator = hass.data[DOMAIN][entry.entry_id]["counts"]

    async_add_entities(
        [
            PiggyTaskFamilySensor(coordinator, entry, description)
            for description in FAMILY_SENSOR_DESCRIPTIONS
        ]
    )

    add_new_children = child_entity_adder(
        coordinator,
        lambda child_id: [
            PiggyTaskChildSensor(coordinator, entry, child_id, description)
            for description in SENSOR_DESCRIPTIONS
        ],
        async_add_entities,
    )
    add_new_children()
    entry.async_on_unload(coordinator.async_add_listener(add_new_children))


class PiggyTaskChildSensor(CoordinatorEntity[PiggyTaskCoordinator], SensorEntity):
    """One task-count sensor for one child."""

    _attr_has_entity_name = True
    entity_description: PiggyTaskSensorDescription

    def __init__(
        self,
        coordinator: PiggyTaskCoordinator,
        entry: ConfigEntry,
        child_id: str,
        description: PiggyTaskSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._child_id = child_id
        self._attr_unique_id = f"{entry.entry_id}_{child_id}_{description.key}"

    def _child(self) -> ChildTaskCounts | None:
        return next((c for c in self.coordinator.data.children if c.id == self._child_id), None)

    @property
    def native_value(self) -> int | None:
        child = self._child()
        return self.entity_description.value_fn(child) if child else None

    @property
    def available(self) -> bool:
        return super().available and self._child() is not None

    @property
    def device_info(self) -> DeviceInfo:
        child = self._child()
        name = child.name if child else self._child_id
        return child_device_info(self._child_id, name)


class PiggyTaskFamilySensor(CoordinatorEntity[PiggyTaskCoordinator], SensorEntity):
    """One family-total sensor, aggregated across all children."""

    _attr_has_entity_name = True
    entity_description: PiggyTaskFamilySensorDescription

    def __init__(
        self,
        coordinator: PiggyTaskCoordinator,
        entry: ConfigEntry,
        description: PiggyTaskFamilySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> int:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def device_info(self) -> DeviceInfo:
        return family_device_info(self.coordinator.data.family_id, self.coordinator.data.family_name)
