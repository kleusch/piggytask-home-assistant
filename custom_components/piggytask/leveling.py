"""XP → level conversion, mirroring the app's leveling curve.

The task-counts API computes and returns the level itself (see
`#shared/xp-level` in the main app, which this was ported from). This
module is only a fallback for api.py to use against an older server
that doesn't send "level" yet, so upgrading the integration ahead of a
backend rollout doesn't break the sensor.
"""

from __future__ import annotations

# Below this level, XP needed per level grows linearly (level*2+20). From here
# on it's held flat at LATE_GAME_XP_PER_LEVEL so pace doesn't keep
# accelerating deeper into the game.
_LATE_GAME_LEVEL_CAP = 40

# = totalXpForLevel(_LATE_GAME_LEVEL_CAP) / (_LATE_GAME_LEVEL_CAP - 1), i.e.
# the average XP/level it took to go from level 1 to the cap, so post-cap
# leveling keeps the same pace instead of the ever-steeper linear ramp.
_LATE_GAME_XP_PER_LEVEL = 60

_MAX_LEVEL = 99


def _total_xp_for_level(level: int) -> int:
    """Total cumulative XP needed to reach `level` from zero."""
    if level <= 1:
        return 0
    if level <= _LATE_GAME_LEVEL_CAP:
        return (level - 1) * (level + 20)
    return _total_xp_for_level(_LATE_GAME_LEVEL_CAP) + (level - _LATE_GAME_LEVEL_CAP) * (
        _LATE_GAME_XP_PER_LEVEL
    )


def level_from_xp(total_xp: int) -> int:
    """Return the level reached at `total_xp`, capped at `_MAX_LEVEL`."""
    level = 1
    while level < _MAX_LEVEL and total_xp >= _total_xp_for_level(level + 1):
        level += 1
    return level
