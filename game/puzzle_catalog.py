"""
Каталог логических пазлов сапёра: один ход — открой клетку, которую можно вывести из подсказок.
У каждого пазла множество допустимых клеток solution (любая из них считается верным ответом).
"""
from __future__ import annotations

import time
from typing import Any

from django.utils.translation import gettext_lazy as _

from .engine import _calc_numbers


def _state_from_spec(
    spec: dict[str, Any],
) -> dict:
    rows: int = spec['rows']
    cols: int = spec['cols']
    mines: set[tuple[int, int]] = set(spec['mines'])
    mine_map = [[False] * cols for _ in range(rows)]
    for r, c in mines:
        mine_map[r][c] = True
    board = _calc_numbers(mine_map, rows, cols)

    revealed = [[False] * cols for _ in range(rows)]
    flagged = [[False] * cols for _ in range(rows)]
    for r, c in spec['revealed']:
        revealed[r][c] = True
    for r, c in spec['flagged']:
        flagged[r][c] = True

    mine_total = len(mines)
    flags_count = sum(1 for r in range(rows) for c in range(cols) if flagged[r][c])
    revealed_count = sum(
        1
        for r in range(rows)
        for c in range(cols)
        if revealed[r][c] and not mine_map[r][c]
    )

    return {
        'rows': rows,
        'cols': cols,
        'mines': mine_total,
        'difficulty': 'puzzle',
        'mode': 'puzzle',
        'board': board,
        'revealed': revealed,
        'flagged': flagged,
        'mine_map': mine_map,
        'status': 'playing',
        'mines_placed': True,
        'start_time': time.time(),
        'end_time': None,
        'flags_count': flags_count,
        'revealed_count': revealed_count,
        'puzzle_id': spec['id'],
        'puzzle_tier': spec['tier'],
        'solution_cells': frozenset(spec['solution']),
        'teacher_note': spec['teacher_note'],
    }


# id, tier (сложность по мере роста), координаты 0-based
PUZZLE_SPECS: list[dict[str, Any]] = [
    {
        'id': 1,
        'tier': 1,
        'title': _('«3» и три флага: остальные соседи пустые'),
        'rows': 5,
        'cols': 5,
        'mines': [(2, 0), (2, 1), (2, 2)],
        'revealed': [(1, 1)],
        'flagged': [(2, 0), (2, 1), (2, 2)],
        'solution': [(0, 0), (0, 1), (0, 2), (1, 0), (1, 2)],
        'teacher_note': (
            'When a numbered cell shows 3 and exactly three adjacent cells are already '
            'flagged as mines, every other adjacent hidden cell must be safe to open.'
        ),
    },
    {
        'id': 2,
        'tier': 1,
        'title': _('Угол: «1» и один флаг-мина'),
        'rows': 4,
        'cols': 4,
        'mines': [(0, 1)],
        'revealed': [(0, 0)],
        'flagged': [(0, 1)],
        'solution': [(1, 0), (1, 1)],
        'teacher_note': (
            'A 1 in the corner that already has one flagged neighbor means the mine '
            'requirement is met; the remaining adjacent hidden cells are safe.'
        ),
    },
    {
        'id': 3,
        'tier': 2,
        'title': _('«2» и две отмеченные мины рядом'),
        'rows': 5,
        'cols': 5,
        'mines': [(3, 2), (3, 3)],
        'revealed': [(2, 2)],
        'flagged': [(3, 2), (3, 3)],
        'solution': [(1, 1), (1, 2), (1, 3), (2, 1), (2, 3), (3, 1)],
        'teacher_note': (
            'If 2 is satisfied by exactly two adjacent flags, other adjacent '
            'hidden cells around that 2 are safe.'
        ),
    },
    {
        'id': 4,
        'tier': 2,
        'title': _('Две «1» с одной общей миной'),
        'rows': 5,
        'cols': 5,
        'mines': [(3, 2)],
        'revealed': [(2, 1), (2, 3)],
        'flagged': [(3, 2)],
        'solution': [(1, 0), (1, 1), (1, 2), (1, 3), (1, 4), (2, 0), (2, 2), (2, 4), (3, 1), (3, 3), (3, 4)],
        'teacher_note': (
            'Two 1s that share a single flagged mine on their common corner use up '
            'their mine count; every other adjacent hidden cell is safe to open.'
        ),
    },
    {
        'id': 5,
        'tier': 3,
        'title': _('«3» на поле 7×7'),
        'rows': 7,
        'cols': 7,
        'mines': [(4, 2), (4, 3), (4, 4)],
        'revealed': [(3, 3)],
        'flagged': [(4, 2), (4, 3), (4, 4)],
        'solution': [(2, 2), (2, 3), (2, 4), (3, 2), (3, 4)],
        'teacher_note': (
            'Same logic as a smaller 3-with-three-flags puzzle; scan the 8-neighborhood '
            'and open any cell that is not flagged as a mine and touches the clue.'
        ),
    },
    {
        'id': 6,
        'tier': 3,
        'title': _('«4» и четыре мины по углам окрестности'),
        'rows': 7,
        'cols': 7,
        'mines': [(2, 2), (2, 4), (4, 2), (4, 4)],
        'revealed': [(3, 3)],
        'flagged': [(2, 2), (2, 4), (4, 2), (4, 4)],
        'solution': [(2, 3), (3, 2), (3, 4), (4, 3)],
        'teacher_note': (
            'When a 4 has its four mines fully marked on the diagonal touches of its '
            '8-neighborhood, the remaining four orthogonal neighbors are safe.'
        ),
    },
    {
        'id': 7,
        'tier': 4,
        'title': _('Три флага под «3»'),
        'rows': 8,
        'cols': 8,
        'mines': [(3, 3), (3, 4), (3, 5)],
        'revealed': [(2, 4)],
        'flagged': [(3, 3), (3, 4), (3, 5)],
        'solution': [(1, 3), (1, 4), (1, 5), (2, 3), (2, 5)],
        'teacher_note': (
            'Same counting idea as beginner puzzles: a 3 with three flags beneath it '
            'uses all mines touching the clue, so the hidden cells above the clue line are safe.'
        ),
    },
]

_PUZZLE_SPECS_BY_ID = {p['id']: p for p in PUZZLE_SPECS}


def get_puzzle_spec(puzzle_id: int) -> dict[str, Any] | None:
    return _PUZZLE_SPECS_BY_ID.get(puzzle_id)


def all_puzzle_specs() -> list[dict[str, Any]]:
    return list(PUZZLE_SPECS)


def build_puzzle_state(puzzle_id: int) -> dict | None:
    spec = get_puzzle_spec(puzzle_id)
    if not spec:
        return None
    return _state_from_spec(spec)


def verify_specs() -> None:
    """Отладка: проверить числа и множества solution (pytest/ручной вызов)."""
    for spec in PUZZLE_SPECS:
        st = _state_from_spec(spec)
        for r, c in spec['solution']:
            assert not st['mine_map'][r][c], (spec['id'], r, c)
        for r, c in spec['mines']:
            assert st['mine_map'][r][c]
        for r, c in spec['revealed']:
            assert st['revealed'][r][c]
            assert not st['mine_map'][r][c]
