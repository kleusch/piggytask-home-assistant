# PiggyTask — Home Assistant Integration

[HACS](https://hacs.xyz/) custom integration for [PiggyTask](https://piggytask.de) (family chores & homework tracking). Config-flow setup — paste an API token, done. Adds five sensors per child (tasks + rewards) plus one family-total sensor, and with a Premium token, a to-do list per child.

[![Add repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=kleusch&repository=piggytask-home-assistant&category=integration)

File issues/PRs in this repo.

## Contents

- [What's included](#whats-included)
- [Sensors](#sensors)
- [To-do list (Premium, optional)](#to-do-list-premium-optional)
- [Example automations](#example-automations)
- [Get an API token](#get-an-api-token)
- [Install](#install)
- [License](#license)

## What's included

| File                                          | Purpose                                                        |
| ---------------------------------------------- | --------------------------------------------------------------- |
| `custom_components/piggytask/manifest.json`   | Integration manifest (domain `piggytask`)                     |
| `custom_components/piggytask/config_flow.py`  | UI setup: paste an API token, validated immediately            |
| `custom_components/piggytask/coordinator.py`  | Polls `task-counts` (sensors) and `tasks` (to-do), every 5 min |
| `custom_components/piggytask/sensor.py`       | Sensors per child, plus one family-total sensor                 |
| `custom_components/piggytask/leveling.py`     | XP → level fallback for older servers that don't send `level` yet |
| `custom_components/piggytask/todo.py`         | To-do list per child, mark-done only (no create/delete)         |
| `custom_components/piggytask/entity.py`       | Shared device-info helpers (one device per child + one for the family) |
| `hacs.json`                                   | HACS repository metadata                                       |

## Sensors

One device per active child ("PiggyTask – `<name>`"):

- `sensor.piggytask_<name>_open_tasks` — open tasks
- `sensor.piggytask_<name>_overdue_tasks` — overdue tasks
- `sensor.piggytask_<name>_due_today` — due today
- `sensor.piggytask_<name>_coin_balance` — current coin balance
- `sensor.piggytask_<name>_xp_balance` — current XP balance
- `sensor.piggytask_<name>_level` — current level (1–99), same curve as the app's level-ups

New children show up as new entities automatically once they're active in the app (no restart needed).

Plus one family-level sensor (its own device, "PiggyTask – `<family name>`"), handy for a single
automation instead of templating over every child:

- `sensor.piggytask_family_open_tasks` — open tasks, summed across all children

## To-do list (Premium, optional)

If the token you paste has the `tasks:complete` scope (the "Counters + check off" preset when creating a token in the PiggyTask app, requires Premium), the integration also creates a `todo.piggytask_<name>` entity per child — open tasks as a checkable list. Checking an item off calls PiggyTask's task-complete API (awards coins/XP, same as completing it in the app). No creating, assigning, or reopening tasks from Home Assistant — completion only.

Whether the to-do platform loads is decided automatically at startup (an initial fetch against the tasks API) — counters-only tokens simply get the sensors.

## Example automations

Notify when a child has an overdue task (adjust the entity id to your child's name slug, e.g. `max`):

```yaml
automation:
  - alias: 'PiggyTask: overdue task'
    trigger:
      - platform: numeric_state
        entity_id: sensor.piggytask_max_overdue_tasks
        above: 0
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: 'PiggyTask'
          message: 'Max has an overdue task.'
```

Evening reminder if anything is still open, using the family-total sensor instead of listing every child:

```yaml
automation:
  - alias: 'PiggyTask: open tasks in the evening'
    trigger:
      - platform: time
        at: '19:00:00'
    condition:
      - condition: numeric_state
        entity_id: sensor.piggytask_family_open_tasks
        above: 0
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: 'PiggyTask'
          message: >
            {{ states('sensor.piggytask_family_open_tasks') }} task(s) still open today.
```

## Get an API token

In the PiggyTask app: **Parent settings → Integrations → Home Assistant** → name it, pick a preset ("Counters only", free, or "Counters + check off", Premium) → create. The token is shown once — copy it before closing.

## Install

### HACS

[![Add repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=kleusch&repository=piggytask-home-assistant&category=integration)

Click the button (needs [My Home Assistant](https://www.home-assistant.io/integrations/my/) linked to your instance), or manually: HACS → Integrations → Custom repositories → add this repo's URL, category "Integration". Then install PiggyTask, **restart Home Assistant** (Settings → System → Restart — without a restart, Home Assistant doesn't know about the integration yet, and "Add Integration" fails with "This integration does not support configuration via the user interface"), and:

[![Add PiggyTask integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=piggytask)

— or manually **Settings → Devices & Services → Add Integration → PiggyTask** — and paste the token.

### Manual

```sh
cp -r custom_components/piggytask <config>/custom_components/piggytask
```

Restart Home Assistant → **Settings → Devices & Services → Add Integration → PiggyTask** → paste the API token.

## License

MIT — see [LICENSE](LICENSE).
