"""Todo platform for PiggyTask — one to-do list per child, mark-as-done only.

Only set up when the configured token has task read/complete scope (see
__init__.py's async_probe_task_access call) — a counts-only token never gets here.
"""

from __future__ import annotations

from datetime import date

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PiggyTaskCoordinator, PiggyTaskTasksCoordinator
from .entity import child_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up one to-do list entity per active child."""
    data = hass.data[DOMAIN][entry.entry_id]
    counts_coordinator: PiggyTaskCoordinator = data["counts"]
    tasks_coordinator: PiggyTaskTasksCoordinator = data["tasks"]
    known_child_ids: set[str] = set()

    @callback
    def _add_new_children() -> None:
        new_entities: list[PiggyTaskChildTodoList] = []
        for child in counts_coordinator.data.children:
            if child.id in known_child_ids:
                continue
            known_child_ids.add(child.id)
            new_entities.append(
                PiggyTaskChildTodoList(tasks_coordinator, counts_coordinator, entry, child.id)
            )
        if new_entities:
            async_add_entities(new_entities)

    _add_new_children()
    entry.async_on_unload(counts_coordinator.async_add_listener(_add_new_children))


class PiggyTaskChildTodoList(CoordinatorEntity[PiggyTaskTasksCoordinator], TodoListEntity):
    """Open tasks for one child, as a Home Assistant to-do list."""

    _attr_has_entity_name = True
    _attr_translation_key = "task_list"
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    def __init__(
        self,
        tasks_coordinator: PiggyTaskTasksCoordinator,
        counts_coordinator: PiggyTaskCoordinator,
        entry: ConfigEntry,
        child_id: str,
    ) -> None:
        super().__init__(tasks_coordinator)
        self._counts_coordinator = counts_coordinator
        self._child_id = child_id
        self._attr_unique_id = f"{entry.entry_id}_{child_id}_todo"

    def _child_name(self) -> str:
        child = next(
            (c for c in self._counts_coordinator.data.children if c.id == self._child_id), None
        )
        return child.name if child else self._child_id

    @property
    def todo_items(self) -> list[TodoItem]:
        items: list[TodoItem] = []
        for task in self.coordinator.data:
            if task.child_id != self._child_id:
                continue
            due = date.fromisoformat(task.due[:10]) if task.due else None
            items.append(
                TodoItem(uid=task.id, summary=task.summary, status=TodoItemStatus.NEEDS_ACTION, due=due)
            )
        return items

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Mark a task done. PiggyTask has no "reopen" API, so only completion is allowed."""
        if item.status != TodoItemStatus.COMPLETED:
            raise HomeAssistantError(
                "PiggyTask tasks can only be marked done from Home Assistant, not reopened"
            )
        if item.uid is None:
            raise HomeAssistantError("Missing task id")
        await self.coordinator.client.async_complete_task(item.uid, self._child_id)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> DeviceInfo:
        return child_device_info(self._child_id, self._child_name())
