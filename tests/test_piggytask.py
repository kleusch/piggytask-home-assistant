from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.piggytask.const import DOMAIN

BASE = "https://app.piggytask.de"
COUNTS = f"{BASE}/api/integrations/home-assistant/task-counts"
LLM = f"{BASE}/api/integrations/llm/tasks"

CHILDREN = [
    {"id": "c1", "name": "Max", "openTasks": 2, "overdueTasks": 1, "dueToday": 1,
     "coinBalance": 10, "xpBalance": 50, "level": 2},
    {"id": "c2", "name": "Lena", "openTasks": 0, "overdueTasks": 0, "dueToday": 0,
     "coinBalance": 5, "xpBalance": 0, "level": 1},
]
TASKS = [
    {"id": "t1", "childId": "c1", "summary": "Mathe", "due": "2026-10-14T00:00:00Z"},
    {"id": "t2", "childId": "c2", "summary": "Zimmer", "due": None},
]


def payload(**extra):
    return {"family": {"id": "f1", "name": "Fam"}, "children": CHILDREN, **extra}


def entry():
    e = MockConfigEntry(domain=DOMAIN, unique_id="f1",
                        data={"api_token": "tok", "base_url": BASE})
    return e


async def setup_entry(hass, e):
    e.add_to_hass(hass)
    assert await hass.config_entries.async_setup(e.entry_id)
    await hass.async_block_till_done()


def ents(hass, platform):
    return [x for x in er.async_get(hass).entities.values() if x.platform == DOMAIN and x.domain == platform]


async def test_single_request_with_tasks(hass, aioclient_mock):
    aioclient_mock.get(COUNTS, json=payload(tasks=TASKS))
    e = entry()
    await setup_entry(hass, e)
    assert e.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][1].query["include"] == "tasks"
    assert len(ents(hass, "todo")) == 2
    assert len(ents(hass, "sensor")) >= 2 * 6 + 1
    coord = hass.data[DOMAIN][e.entry_id]["counts"]
    assert coord.update_interval == timedelta(minutes=15)


async def test_tasks_null_no_todo(hass, aioclient_mock):
    aioclient_mock.get(COUNTS, json=payload(tasks=None))
    e = entry()
    await setup_entry(hass, e)
    assert e.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 1
    assert ents(hass, "todo") == []
    assert len(ents(hass, "sensor")) >= 13


async def test_fallback_without_tasks_key(hass, aioclient_mock):
    aioclient_mock.get(COUNTS, json=payload())
    aioclient_mock.get(LLM, json={"tasks": TASKS})
    e = entry()
    await setup_entry(hass, e)
    assert len(ents(hass, "todo")) == 2
    assert aioclient_mock.call_count == 2
    assert any("llm/tasks" in str(c[1]) for c in aioclient_mock.mock_calls)


async def test_options_reload_interval(hass, aioclient_mock):
    aioclient_mock.get(COUNTS, json=payload(tasks=TASKS))
    e = entry()
    await setup_entry(hass, e)
    old = hass.data[DOMAIN][e.entry_id]["counts"]
    result = await hass.config_entries.options.async_init(e.entry_id)
    assert result["type"] == "form" and result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval_minutes": 60})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert e.state is ConfigEntryState.LOADED
    new = hass.data[DOMAIN][e.entry_id]["counts"]
    assert new is not old
    assert new.update_interval == timedelta(minutes=60)


async def test_todo_unavailable_when_tasks_become_null(hass, aioclient_mock):
    aioclient_mock.get(COUNTS, json=payload(tasks=TASKS))
    e = entry()
    await setup_entry(hass, e)
    todo_ids = [x.entity_id for x in ents(hass, "todo")]
    assert todo_ids and all(hass.states.get(i).state != "unavailable" for i in todo_ids)
    aioclient_mock.clear_requests()
    aioclient_mock.get(COUNTS, json=payload(tasks=None))
    await hass.data[DOMAIN][e.entry_id]["counts"].async_refresh()
    await hass.async_block_till_done()
    assert all(hass.states.get(i).state == "unavailable" for i in todo_ids)


def test_level_curve_is_monotonic():
    from custom_components.piggytask.leveling import _total_xp_for_level

    needed = [_total_xp_for_level(n + 1) - _total_xp_for_level(n) for n in range(1, 99)]
    assert needed == sorted(needed)
