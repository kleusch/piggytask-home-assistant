"""Thin async client for the PiggyTask Home Assistant API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .const import TASK_COUNTS_PATH, TASKS_COMPLETE_PATH, TASKS_PATH
from .leveling import level_from_xp


class PiggyTaskApiError(Exception):
    """Base error for the PiggyTask API."""


class PiggyTaskAuthError(PiggyTaskApiError):
    """Raised when the API token is missing, invalid, or revoked."""


class PiggyTaskConnectionError(PiggyTaskApiError):
    """Raised when the PiggyTask API cannot be reached."""


@dataclass
class ChildTaskCounts:
    """Task counts and reward balances for a single child."""

    id: str
    name: str
    open_tasks: int
    overdue_tasks: int
    due_today: int
    coin_balance: int
    xp_balance: int
    level: int


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
    """Async client for the PiggyTask Home Assistant / LLM task endpoints."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, api_token: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        auth_error_message: str,
        params: dict[str, str] | None = None,
        json_body: dict[str, str] | None = None,
        ok_statuses: tuple[int, ...] = (200,),
    ) -> Any | None:
        """Shared request/error handling.

        Returns the parsed JSON body for a 200 response, or None for any other
        status in ok_statuses (e.g. 409 "already completed", which has no body).
        """
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers={"x-api-key": self._api_token},
                params=params,
                json=json_body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status in (401, 403):
                    raise PiggyTaskAuthError(auth_error_message)
                if response.status not in ok_statuses:
                    raise PiggyTaskConnectionError(
                        f"Unexpected response {response.status} from PiggyTask"
                    )
                if response.status != 200:
                    return None
                return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PiggyTaskConnectionError(str(err)) from err

    async def async_get_task_counts(self) -> TaskCountsResult:
        """Fetch and parse the current task counts for the token's family."""
        payload = await self._request(
            "GET", TASK_COUNTS_PATH, auth_error_message="Invalid or revoked API token"
        )

        family = payload.get("family") or {}
        children = []
        for child in payload.get("children", []):
            xp_balance = int(child.get("xpBalance", 0))
            # The API computes and returns the level itself (same curve as the app).
            # Fall back to computing it locally only against an older server that
            # doesn't send "level" yet, so this keeps working across a rollout.
            level = int(child["level"]) if child.get("level") is not None else level_from_xp(xp_balance)
            children.append(
                ChildTaskCounts(
                    id=str(child["id"]),
                    name=str(child.get("name", "")),
                    open_tasks=int(child.get("openTasks", 0)),
                    overdue_tasks=int(child.get("overdueTasks", 0)),
                    due_today=int(child.get("dueToday", 0)),
                    coin_balance=int(child.get("coinBalance", 0)),
                    xp_balance=xp_balance,
                    level=level,
                )
            )
        return TaskCountsResult(
            family_id=str(family.get("id", "")),
            family_name=str(family.get("name") or "PiggyTask"),
            children=children,
        )

    async def async_get_tasks(self) -> list[TaskItem]:
        """Fetch open (needs_action) tasks. Requires family:read + tasks:read scope."""
        payload = await self._request(
            "GET",
            TASKS_PATH,
            auth_error_message="Token lacks task read access",
            params={"status": "needs_action"},
        )

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
        """Mark a task done. Requires tasks:complete scope. 409 (already done) is not an error."""
        await self._request(
            "POST",
            TASKS_COMPLETE_PATH,
            auth_error_message="Token lacks tasks:complete scope",
            json_body={"taskId": task_id, "childId": child_id},
            ok_statuses=(200, 409),
        )
