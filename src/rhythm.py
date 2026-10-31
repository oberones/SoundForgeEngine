"""Shared step masks; song indexes these by elapsed section steps."""
PATTERNS = {
    'four_on_floor': [True, False, False, False, True, False, False, False],
    'offbeat': [False, True, False, True, False, True, False, True],
    'every_other': [True, False, True, False, True, False, True, False],
    'syncopated': [True, False, True, True, False, True, False, False],
    'dense': [True, True, False, True, True, False, True, True],
    'sparse': [True, False, False, False, False, False, True, False],
    'all_on': [True] * 8,
    'all_off': [False] * 8
}
