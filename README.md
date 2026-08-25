# PiggyTask — Home Assistant Integration

[HACS](https://hacs.xyz/) custom integration for [PiggyTask](https://piggytask.de) (family chores & homework tracking). Config-flow setup — paste an API token, done. Adds sensors and, with a Premium token, a to-do list per child.


## What's included

| File                                          | Purpose                                                        |
| ---------------------------------------------- | --------------------------------------------------------------- |
| `custom_components/piggytask/manifest.json`   | Integration manifest (domain `piggytask`)                     |
| `custom_components/piggytask/config_flow.py`  | UI setup: paste an API token, validated immediately            |
| `custom_components/piggytask/coordinator.py`  | Polls `task-counts` (sensors) and `tasks` (to-do), every 5 min |
| `custom_components/piggytask/sensor.py`       | 3 sensors per child: open / overdue / due today                |
| `custom_components/piggytask/todo.py`         | To-do list per child, mark-done only (no create/delete)         |
| `custom_components/piggytask/entity.py`       | Shared device-info helper (one device per child)                |
| `hacs.json`                                   | HACS repository metadata                                       |

## Sensors

One device per active child ("PiggyTask – `<name>`"):

- `sensor.piggytask_<name>_open_tasks` — open tasks
- `sensor.piggytask_<name>_overdue_tasks` — overdue tasks
- `sensor.piggytask_<name>_due_today` — due today

New children show up as new entities automatically once they're active in the app (no restart needed).

## To-do list (Premium, optional)

If the token you paste has the `tasks:complete` scope (the "Counters + check off" preset when creating a token in the PiggyTask app, requires Premium), the integration also creates a `todo.piggytask_<name>` entity per child — open tasks as a checkable list. Checking an item off calls PiggyTask's task-complete API (awards coins/XP, same as completing it in the app). No creating, assigning, or reopening tasks from Home Assistant — completion only.

Whether the to-do platform loads is decided automatically at startup (one probe call against the tasks API) — counters-only tokens simply get the sensors.

## Get an API token

In the PiggyTask app: **Parent settings → Integrations → Home Assistant** → name it, pick a preset ("Counters only", free, or "Counters + check off", Premium) → create. The token is shown once — copy it before closing.

## Install

### HACS

HACS → Integrations → Custom repositories → add this repo's URL, category "Integration". Then install normally via the integration search, or **Settings → Devices & Services → Add Integration → PiggyTask** and paste the token.

### Manual

```sh
cp -r custom_components/piggytask <config>/custom_components/piggytask
```

Restart Home Assistant → **Settings → Devices & Services → Add Integration → PiggyTask** → paste the API token.

## Limitations / possible extensions

- Tasks can only be completed, not created, assigned, or reopened (HA tokens don't get `tasks:write`/`pool:*` scopes) — deliberately left to the app, Alexa, or MCP.
- Fixed 5-minute poll interval. No options flow yet — nothing else to configure.

## License

MIT — see [LICENSE](LICENSE).
