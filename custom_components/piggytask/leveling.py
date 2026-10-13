"""XP → level conversion, mirroring the app's leveling curve.

The task-counts API computes and returns the level itself (see
`#shared/xp-level` in the main app, which this was ported from). This
module is only a fallback for api.py to use against an older server
that doesn't send "level" yet, so upgrading the integration ahead of a
backend rollout doesn't break the sensor.
"""

from __future__ import annotations

# Below this level, XP needed per level grows linearly (level*2+20). From here
# on growth slows to a small flat increment per level (_LATE_GAME_XP_STEP) so
# pace doesn't keep accelerating deeper into the game.
_LATE_GAME_LEVEL_CAP = 40

# = xpToNextLevel(_LATE_GAME_LEVEL_CAP - 1), i.e. the highest requirement the
# linear ramp reaches right before the cap. Used as the floor for the
# late-game curve so it never asks for less XP than a lower level already
# did (a flat, much lower _LATE_GAME_XP_PER_LEVEL used to cause exactly
# that: e.g. level 45 needing less XP than level 37).
_LATE_GAME_BASE_XP = (_LATE_GAME_LEVEL_CAP - 1) * 2 + 20

# Small per-level increase applied from the cap onward — much gentler than
# the pre-cap ramp (+2/level), so leveling stays fast but keeps climbing
# instead of plateauing (or worse, dropping) once flattened out.
_LATE_GAME_XP_STEP = 1

_MAX_LEVEL = 99


def _total_xp_for_level(level: int) -> int:
    """Total cumulative XP needed to reach `level` from zero."""
    if level <= 1:
        return 0
    if level <= _LATE_GAME_LEVEL_CAP:
        return (level - 1) * (level + 20)
    n = level - _LATE_GAME_LEVEL_CAP
    return (
        _total_xp_for_level(_LATE_GAME_LEVEL_CAP)
        + _LATE_GAME_BASE_XP * n
        + (_LATE_GAME_XP_STEP * n * (n + 1)) // 2
    )


def level_from_xp(total_xp: int) -> int:
    """Return the level reached at `total_xp`, capped at `_MAX_LEVEL`."""
    level = 1
    while level < _MAX_LEVEL and total_xp >= _total_xp_for_level(level + 1):
        level += 1
    return level
