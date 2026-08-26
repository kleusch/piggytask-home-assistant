"""Shared helpers for PiggyTask entities: device grouping and per-child entity setup."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import PiggyTaskCoordinator


def _device_info(entity_id: str, name: str, model: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entity_id)},
        name=f"PiggyTask – {name}",
        manufacturer="PiggyTask",
        model=model,
        configuration_url="https://app.piggytask.de",
    )


def child_device_info(child_id: str, child_name: str) -> DeviceInfo:
    """Build the DeviceInfo grouping all entities for one child."""
    return _device_info(child_id, child_name, "Child")


def family_device_info(family_id: str, family_name: str) -> DeviceInfo:
    """Build the DeviceInfo for family-level entities (e.g. a total-across-children sensor)."""
    return _device_info(family_id, family_name, "Family")


def child_entity_adder(
    counts_coordinator: PiggyTaskCoordinator,
    make_entities: Callable[[str], list[Entity]],
    async_add_entities: AddEntitiesCallback,
) -> Callable[[], None]:
    """Build a callback that adds entities for any child not yet seen.

    Shared by sensor.py and todo.py: both add a fixed set of per-child entities as
    soon as a child shows up in the counts coordinator, and again whenever a new
    child appears later — call the returned callback once immediately, then register
    it via counts_coordinator.async_add_listener() for subsequent updates.
    """
    known_child_ids: set[str] = set()

    @callback
    def _add_new_children() -> None:
        new_entities: list[Entity] = []
        for child in counts_coordinator.data.children:
            if child.id in known_child_ids:
                continue
            known_child_ids.add(child.id)
            new_entities.extend(make_entities(child.id))
        if new_entities:
            async_add_entities(new_entities)

    return _add_new_children
