import random
import time
from typing import Optional

DIFFICULTIES = {
    'beginner':     {'rows': 9,  'cols': 9,  'mines': 10},
    'intermediate': {'rows': 16, 'cols': 16, 'mines': 40},
    'expert':       {'rows': 16, 'cols': 30, 'mines': 99},
}
def create_game(difficulty: str = 'beginner',
                rows: Optional[int] = None,
                cols: Optional[int] = None,
                mines: Optional[int] = None) -> dict:
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
        'board': board,
        'revealed': [[False] * cols for _ in range(rows)],
        'flagged': [[False] * cols for _ in range(rows)],
        'mine_map': [[False] * cols for _ in range(rows)],
        'status': 'ready',  #ready / playing/ won/ lost
        'mines_placed': False,
        'start_time': None,
        'end_time': None,
        'flags_count': 0,
        'revealed_count': 0,
    }


def _place_mines(state: dict, safe_row: int, safe_col: int):
    #REDO
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

    # считаем цифры (сколько мин вокруг каждой клетки)
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

    state['mine_map'] = mine_map
    state['board'] = board
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

    if state['mine_map'][row][col]:
        state['status'] = 'lost'
        state['end_time'] = time.time()
        for r in range(state['rows']):
            for c in range(state['cols']):
                if state['mine_map'][r][c]:
                    state['revealed'][r][c] = True
        return state

    _flood_fill(state, row, col)
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
        #flags on mines after win
        for r in range(state['rows']):
            for c in range(state['cols']):
                if state['mine_map'][r][c]:
                    state['flagged'][r][c] = True
        state['flags_count'] = state['mines']


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

    return {
        'rows': rows,
        'cols': cols,
        'mines': state['mines'],
        'difficulty': state['difficulty'],
        'status': state['status'],
        'flags_count': state['flags_count'],
        'elapsed': get_elapsed(state),
        'cells': cells,
    }
