"""Thin async client for the PiggyTask Home Assistant API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import aiohttp

from .const import TASK_COUNTS_PATH, TASKS_COMPLETE_PATH, TASKS_PATH


class PiggyTaskApiError(Exception):
    """Base error for the PiggyTask API."""


class PiggyTaskAuthError(PiggyTaskApiError):
    """Raised when the API token is missing, invalid, or revoked."""


class PiggyTaskConnectionError(PiggyTaskApiError):
    """Raised when the PiggyTask API cannot be reached."""


@dataclass
class ChildTaskCounts:
    """Task counts for a single child."""

    id: str
    name: str
    open_tasks: int
    overdue_tasks: int
    due_today: int


@dataclass
class TaskCountsResult:
    """Response of the task-counts endpoint."""

    family_id: str
    family_name: str
    children: list[ChildTaskCounts] = field(default_factory=list)


@dataclass
class TaskItem:
    """A single open (needs_action) task."""

    id: str
    child_id: str
    summary: str
    due: str | None


class PiggyTaskApiClient:
    """Wraps GET /api/integrations/home-assistant/task-counts."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_token: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token

    async def async_get_task_counts(self) -> TaskCountsResult:
        """Fetch and parse the current task counts for the token's family."""
        url = f"{self._base_url}{TASK_COUNTS_PATH}"
        try:
            async with self._session.get(
                url,
                headers={"x-api-key": self._api_token},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status in (401, 403):
                    raise PiggyTaskAuthError("Invalid or revoked API token")
                if response.status != 200:
                    raise PiggyTaskConnectionError(
                        f"Unexpected response {response.status} from PiggyTask"
                    )
                payload = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PiggyTaskConnectionError(str(err)) from err

        family = payload.get("family") or {}
        children = [
            ChildTaskCounts(
                id=str(child["id"]),
                name=str(child.get("name", "")),
                open_tasks=int(child.get("openTasks", 0)),
                overdue_tasks=int(child.get("overdueTasks", 0)),
                due_today=int(child.get("dueToday", 0)),
            )
            for child in payload.get("children", [])
        ]
        return TaskCountsResult(
            family_id=str(family.get("id", "")),
            family_name=str(family.get("name") or "PiggyTask"),
            children=children,
        )

    async def async_get_tasks(self) -> list[TaskItem]:
        """Fetch open (needs_action) tasks. Requires family:read + tasks:read scope."""
        url = f"{self._base_url}{TASKS_PATH}"
        try:
            async with self._session.get(
                url,
                headers={"x-api-key": self._api_token},
                params={"status": "needs_action"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status in (401, 403):
                    raise PiggyTaskAuthError("Token lacks task read access")
                if response.status != 200:
                    raise PiggyTaskConnectionError(
                        f"Unexpected response {response.status} from PiggyTask"
                    )
                payload = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PiggyTaskConnectionError(str(err)) from err

        return [
            TaskItem(
                id=str(task["id"]),
                child_id=str(task["childId"]),
                summary=str(task.get("summary", "")),
                due=task.get("due"),
            )
            for task in payload.get("tasks", [])
        ]

    async def async_complete_task(self, task_id: str, child_id: str) -> None:
        """Mark a task done. Requires tasks:complete scope."""
        url = f"{self._base_url}{TASKS_COMPLETE_PATH}"
        try:
            async with self._session.post(
                url,
                headers={"x-api-key": self._api_token},
                json={"taskId": task_id, "childId": child_id},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status in (401, 403):
                    raise PiggyTaskAuthError("Token lacks tasks:complete scope")
                if response.status == 409:
                    return  # already completed elsewhere — nothing left to do
                if response.status != 200:
                    raise PiggyTaskConnectionError(
                        f"Unexpected response {response.status} from PiggyTask"
                    )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PiggyTaskConnectionError(str(err)) from err
