"""Shared quarter-note timing units, independent of pattern traversal."""

BEATS_PER_BAR = 4
DIVISION_BEATS = {'whole': 4.0, 'half': 2.0, 'quarter': 1.0,
                  'eighth': 0.5, 'sixteenth': 0.25}


def step_beats(division: str) -> float:
    """Return a pattern step's duration in quarter-note beats."""
    return DIVISION_BEATS.get(division, 0.25)
