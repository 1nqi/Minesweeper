import random
import time
import hashlib
from datetime import date
from typing import Optional

DIFFICULTIES = {
    'beginner':     {'rows': 9,  'cols': 9,  'mines': 10},
    'intermediate': {'rows': 16, 'cols': 16, 'mines': 40},
    'expert':       {'rows': 16, 'cols': 30, 'mines': 99},
}

VALID_MODES = ('classic', 'speed', 'noflag', 'daily', 'blind', 'infinite')


def create_game(difficulty: str = 'beginner',
                rows: Optional[int] = None,
                cols: Optional[int] = None,
                mines: Optional[int] = None,
                mode: str = 'classic') -> dict:
    if mode not in VALID_MODES:
        mode = 'classic'

    if mode == 'daily':
        return _create_daily_game(difficulty)

    if difficulty in DIFFICULTIES and rows is None:
        cfg = DIFFICULTIES[difficulty]
        rows, cols, mines = cfg['rows'], cfg['cols'], cfg['mines']
    else:
        rows = rows or 9
        cols = cols or 9
        mines = mines or 10

    max_mines = rows * cols - 9
    mines = min(mines, max(1, max_mines))

    board = [[0] * cols for _ in range(rows)]

    return {
        'rows': rows,
        'cols': cols,
        'mines': mines,
        'difficulty': difficulty,
        'mode': mode,
        'board': board,
        'revealed': [[False] * cols for _ in range(rows)],
        'flagged': [[False] * cols for _ in range(rows)],
        'mine_map': [[False] * cols for _ in range(rows)],
        'status': 'ready',
        'mines_placed': False,
        'start_time': None,
        'end_time': None,
        'flags_count': 0,
        'revealed_count': 0,
    }


def _create_daily_game(difficulty: str = 'beginner') -> dict:
    if difficulty not in DIFFICULTIES:
        difficulty = 'beginner'
    cfg = DIFFICULTIES[difficulty]
    rows, cols, mines = cfg['rows'], cfg['cols'], cfg['mines']

    today = date.today().isoformat()
    seed_str = f"minesweeper-daily-{today}-{difficulty}"
    seed = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16) % (2**32)

    rng = random.Random(seed)

    safe_row, safe_col = rows // 2, cols // 2
    safe_zone = set()
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            nr, nc = safe_row + dr, safe_col + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                safe_zone.add((nr, nc))

    candidates = [(r, c) for r in range(rows) for c in range(cols) if (r, c) not in safe_zone]
    chosen = rng.sample(candidates, min(mines, len(candidates)))

    mine_map = [[False] * cols for _ in range(rows)]
    for r, c in chosen:
        mine_map[r][c] = True

    board = _calc_numbers(mine_map, rows, cols)

    return {
        'rows': rows,
        'cols': cols,
        'mines': mines,
        'difficulty': difficulty,
        'mode': 'daily',
        'board': board,
        'revealed': [[False] * cols for _ in range(rows)],
        'flagged': [[False] * cols for _ in range(rows)],
        'mine_map': mine_map,
        'status': 'ready',
        'mines_placed': True,
        'daily_seed': seed_str,
        'start_time': None,
        'end_time': None,
        'flags_count': 0,
        'revealed_count': 0,
    }


def get_daily_info() -> dict:
    today = date.today()
    day_num = (today - date(2026, 1, 1)).days + 1
    return {
        'date': today.isoformat(),
        'day_number': day_num,
    }


def _daily_relocate_mine(state: dict, row: int, col: int):
    """Move a mine away from the first click in daily mode."""
    rows, cols = state['rows'], state['cols']
    safe_zone = set()
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            nr, nc = row + dr, col + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                safe_zone.add((nr, nc))

    state['mine_map'][row][col] = False

    for r in range(rows):
        for c in range(cols):
            if not state['mine_map'][r][c] and (r, c) not in safe_zone:
                state['mine_map'][r][c] = True
                break
        else:
            continue
        break

    state['board'] = _calc_numbers(state['mine_map'], rows, cols)


def _calc_numbers(mine_map, rows, cols):
    board = [[0] * cols for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if mine_map[r][c]:
                board[r][c] = -1
            else:
                count = 0
                for dr in range(-1, 2):
                    for dc in range(-1, 2):
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols and mine_map[nr][nc]:
                            count += 1
                board[r][c] = count
    return board


def _place_mines(state: dict, safe_row: int, safe_col: int):
    rows, cols, mines = state['rows'], state['cols'], state['mines']
    safe_zone = set()
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            nr, nc = safe_row + dr, safe_col + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                safe_zone.add((nr, nc))

    candidates = [
        (r, c) for r in range(rows) for c in range(cols)
        if (r, c) not in safe_zone
    ]
    chosen = random.sample(candidates, min(mines, len(candidates)))

    mine_map = [[False] * cols for _ in range(rows)]
    for r, c in chosen:
        mine_map[r][c] = True

    state['mine_map'] = mine_map
    state['board'] = _calc_numbers(mine_map, rows, cols)
    state['mines_placed'] = True


def _flood_fill(state: dict, row: int, col: int):
    rows, cols = state['rows'], state['cols']
    stack = [(row, col)]

    while stack:
        r, c = stack.pop()
        if state['revealed'][r][c] or state['flagged'][r][c]:
            continue

        state['revealed'][r][c] = True
        state['revealed_count'] += 1

        if state['board'][r][c] == 0:
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and not state['revealed'][nr][nc]:
                        stack.append((nr, nc))


def reveal(state: dict, row: int, col: int) -> dict:
    if state['status'] in ('won', 'lost'):
        return state
    if state['flagged'][row][col]:
        return state
    if state['revealed'][row][col]:
        return state

    if not state['mines_placed']:
        _place_mines(state, row, col)
        state['status'] = 'playing'
        state['start_time'] = time.time()
    elif state['status'] == 'ready':
        state['status'] = 'playing'
        state['start_time'] = time.time()
        if state.get('mode') == 'daily' and state['mine_map'][row][col]:
            _daily_relocate_mine(state, row, col)

    if state['mine_map'][row][col]:
        state['status'] = 'lost'
        state['end_time'] = time.time()
        for r in range(state['rows']):
            for c in range(state['cols']):
                if state['mine_map'][r][c]:
                    state['revealed'][r][c] = True
        return state

    _flood_fill(state, row, col)

    if state.get('mode') == 'infinite':
        _try_expand(state, row, col)

    _check_win(state)
    return state


def chord(state: dict, row: int, col: int) -> dict:
    if state['status'] in ('won', 'lost'):
        return state
    if not state['revealed'][row][col]:
        return state

    value = state['board'][row][col]
    if value <= 0:
        return state

    flag_count = 0
    neighbors = []
    for dr in range(-1, 2):
        for dc in range(-1, 2):
            if dr == 0 and dc == 0:
                continue
            nr, nc = row + dr, col + dc
            if 0 <= nr < state['rows'] and 0 <= nc < state['cols']:
                if state['flagged'][nr][nc]:
                    flag_count += 1
                elif not state['revealed'][nr][nc]:
                    neighbors.append((nr, nc))

    if flag_count == value:
        for nr, nc in neighbors:
            reveal(state, nr, nc)

    return state


def toggle_flag(state: dict, row: int, col: int) -> dict:
    if state['status'] in ('won', 'lost'):
        return state
    if state['revealed'][row][col]:
        return state

    if state.get('mode') == 'noflag':
        return state

    if state['status'] == 'ready':
        state['status'] = 'playing'
        state['start_time'] = time.time()

    if state['flagged'][row][col]:
        state['flagged'][row][col] = False
        state['flags_count'] -= 1
    else:
        state['flagged'][row][col] = True
        state['flags_count'] += 1

    return state


def _check_win(state: dict):
    total_cells = state['rows'] * state['cols']
    if state['revealed_count'] == total_cells - state['mines']:
        state['status'] = 'won'
        state['end_time'] = time.time()
        for r in range(state['rows']):
            for c in range(state['cols']):
                if state['mine_map'][r][c]:
                    state['flagged'][r][c] = True
        state['flags_count'] = state['mines']


def _try_expand(state: dict, row: int, col: int):
    """Infinite mode: expand the board when player reveals near edges."""
    rows, cols = state['rows'], state['cols']
    max_size = 50

    near_top = row <= 1
    near_bot = row >= rows - 2
    near_left = col <= 1
    near_right = col >= cols - 2

    expand_top = near_top and rows < max_size
    expand_bot = near_bot and rows < max_size
    expand_left = near_left and cols < max_size
    expand_right = near_right and cols < max_size

    if not (expand_top or expand_bot or expand_left or expand_right):
        return

    add_rows_top = 3 if expand_top else 0
    add_rows_bot = 3 if expand_bot else 0
    add_cols_left = 3 if expand_left else 0
    add_cols_right = 3 if expand_right else 0

    new_rows = min(rows + add_rows_top + add_rows_bot, max_size)
    new_cols = min(cols + add_cols_left + add_cols_right, max_size)

    add_rows_top = min(add_rows_top, new_rows - rows)
    add_rows_bot = new_rows - rows - add_rows_top
    add_cols_left = min(add_cols_left, new_cols - cols)
    add_cols_right = new_cols - cols - add_cols_left

    new_mine_map = [[False] * new_cols for _ in range(new_rows)]
    new_revealed = [[False] * new_cols for _ in range(new_rows)]
    new_flagged = [[False] * new_cols for _ in range(new_rows)]

    for r in range(rows):
        for c in range(cols):
            nr, nc = r + add_rows_top, c + add_cols_left
            new_mine_map[nr][nc] = state['mine_map'][r][c]
            new_revealed[nr][nc] = state['revealed'][r][c]
            new_flagged[nr][nc] = state['flagged'][r][c]

    empty_cells = []
    for r in range(new_rows):
        for c in range(new_cols):
            if not new_mine_map[r][c] and not new_revealed[r][c]:
                is_old = (add_rows_top <= r < add_rows_top + rows and
                          add_cols_left <= c < add_cols_left + cols)
                if not is_old:
                    empty_cells.append((r, c))

    new_mine_count = max(1, len(empty_cells) // 5)
    if empty_cells:
        new_mines = random.sample(empty_cells, min(new_mine_count, len(empty_cells)))
        for r, c in new_mines:
            new_mine_map[r][c] = True
        state['mines'] += len(new_mines)

    state['mine_map'] = new_mine_map
    state['revealed'] = new_revealed
    state['flagged'] = new_flagged
    state['rows'] = new_rows
    state['cols'] = new_cols
    state['board'] = _calc_numbers(new_mine_map, new_rows, new_cols)


def get_elapsed(state: dict) -> float:
    if state['start_time'] is None:
        return 0.0
    end = state['end_time'] or time.time()
    return round(end - state['start_time'], 1)


def get_client_state(state: dict) -> dict:
    rows, cols = state['rows'], state['cols']
    cells = []

    for r in range(rows):
        row_data = []
        for c in range(cols):
            cell = {'r': r, 'c': c}
            if state['revealed'][r][c]:
                cell['revealed'] = True
                val = state['board'][r][c]
                if val == -1:
                    cell['mine'] = True
                else:
                    cell['value'] = val
            elif state['flagged'][r][c]:
                cell['flagged'] = True
            row_data.append(cell)
        cells.append(row_data)

    result = {
        'rows': rows,
        'cols': cols,
        'mines': state['mines'],
        'difficulty': state['difficulty'],
        'mode': state.get('mode', 'classic'),
        'status': state['status'],
        'flags_count': state['flags_count'],
        'elapsed': get_elapsed(state),
        'cells': cells,
    }

    if state.get('mode') == 'daily':
        result['daily'] = get_daily_info()

    return result
