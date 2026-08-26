"""Sensor platform for PiggyTask — three sensors per active child."""

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

from .api import ChildTaskCounts
from .const import DOMAIN
from .coordinator import PiggyTaskCoordinator
from .entity import child_device_info, child_entity_adder, family_device_info


@dataclass(frozen=True, kw_only=True)
class PiggyTaskSensorDescription(SensorEntityDescription):
    """Describes one of the per-child count sensors."""

    value_fn: Callable[[ChildTaskCounts], int]


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
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up PiggyTask sensors, adding entities as new children appear."""
    coordinator: PiggyTaskCoordinator = hass.data[DOMAIN][entry.entry_id]["counts"]

    async_add_entities([PiggyTaskFamilyOpenTasksSensor(coordinator, entry)])

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


class PiggyTaskFamilyOpenTasksSensor(CoordinatorEntity[PiggyTaskCoordinator], SensorEntity):
    """Total open tasks across all children — one number for a single automation/alert."""

    _attr_has_entity_name = True
    _attr_translation_key = "family_open_tasks"
    _attr_icon = "mdi:clipboard-list-outline"
    _attr_native_unit_of_measurement = "tasks"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: PiggyTaskCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_family_open_tasks"

    @property
    def native_value(self) -> int:
        return sum(child.open_tasks for child in self.coordinator.data.children)

    @property
    def device_info(self) -> DeviceInfo:
        return family_device_info(self.coordinator.data.family_id, self.coordinator.data.family_name)
