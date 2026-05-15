"""Текстовое пояснение к подсказке через Google Gemini (координаты задаёт сервер)."""

from __future__ import annotations

from django.conf import settings


def _lang_name(django_code: str) -> str:
    if not django_code:
        return 'English'
    base = django_code.replace('_', '-').split('-')[0].lower()
    return {
        'ru': 'Russian',
        'en': 'English',
        'kk': 'Kazakh',
    }.get(base, 'English')


def _board_ascii(state: dict) -> tuple[str, int, int]:
    rows, cols = state['rows'], state['cols']
    lines = []
    for r in range(rows):
        chars: list[str] = []
        for c in range(cols):
            if state['flagged'][r][c]:
                chars.append('F')
            elif state['revealed'][r][c]:
                v = state['board'][r][c]
                chars.append('x' if v == -1 else str(v))
            else:
                chars.append('.')
        lines.append(''.join(chars))
    return '\n'.join(lines), rows, cols


def _response_text(resp) -> str:
    try:
        if getattr(resp, 'text', None):
            return (resp.text or '').strip()
    except (ValueError, AttributeError):
        pass
    try:
        cand = resp.candidates[0]
        parts = getattr(cand.content, 'parts', None) or []
        return ''.join(getattr(p, 'text', '') for p in parts).strip()
    except (IndexError, AttributeError, KeyError):
        return ''


def gemini_explain_hint(state: dict, row: int, col: int, language_code: str) -> str:
    """
 Короткий текст для игрока. Без ключа или при ошибке — пустая строка.
    """
    if not getattr(settings, 'GEMINI_HINT_EXPLAIN', True):
        return ''
    api_key = (getattr(settings, 'GEMINI_API_KEY', '') or '').strip()
    if not api_key:
        return ''

    try:
        import google.generativeai as genai
    except ImportError:
        return ''

    grid, r_cnt, c_cnt = _board_ascii(state)
    lang = _lang_name(language_code)
    model_id = (getattr(settings, 'GEMINI_MODEL', '') or 'gemini-2.0-flash').strip()

    prompt = (
        f'You are a Minesweeper tutor. Board is {r_cnt} rows x {c_cnt} cols, 0-based '
        f'(row 0 top, col 0 left).\n'
        f'Legend: . = hidden, F = flag, 0-8 = open cell (adjacent mine count), '
        f'x = mine only if that cell was revealed.\n\n'
        f'{grid}\n\n'
        f'The next safe cell to open is row {row}, column {col} (guaranteed no mine).\n'
        f'Write exactly ONE short sentence in {lang} (max 40 words) using only visible '
        f'clues; give intuition. Do not repeat row/column numbers. No Markdown, no lists.'
    )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_id)
        resp = model.generate_content(
            prompt,
            generation_config={
                'max_output_tokens': 128,
                'temperature': 0.35,
            },
        )
        text = _response_text(resp)
        return text[:500] if text else ''
    except Exception:
        return ''


def gemini_explain_puzzle_mistake(
    state: dict,
    *,
    puzzle_id: int,
    clicked_r: int,
    clicked_c: int,
    kind: str,
    solution_cells: frozenset[tuple[int, int]],
    teacher_note: str,
    language_code: str,
) -> str:
    """
    kind: 'mine' — открыли мину; 'wrong_safe' — открыли не ту безопасную клетку.
    """
    if not getattr(settings, 'GEMINI_HINT_EXPLAIN', True):
        return ''
    api_key = (getattr(settings, 'GEMINI_API_KEY', '') or '').strip()
    if not api_key:
        return ''

    try:
        import google.generativeai as genai
    except ImportError:
        return ''

    grid, r_cnt, c_cnt = _board_ascii(state)
    lang = _lang_name(language_code)
    model_id = (getattr(settings, 'GEMINI_MODEL', '') or 'gemini-2.0-flash').strip()
    sol_list = sorted(solution_cells)
    sol_str = ', '.join(f'({r},{c})' for r, c in sol_list[:12])
    if len(sol_list) > 12:
        sol_str += ', …'

    if kind == 'mine':
        err = 'The player OPENED a cell that contains a mine (game over).'
    else:
        err = (
            'The player opened a safe cell, but it was NOT one of the cells that can be '
            'logically deduced from the current clues and flags alone (not a forced move '
            'for this teaching puzzle).'
        )

    prompt = (
        f'You are a Minesweeper tutor. Puzzle #{puzzle_id} on a {r_cnt}x{c_cnt} board '
        f'(rows and cols are 0-based from top-left).\n'
        f'Board snapshot:\n{grid}\n\n'
        f'{err}\n'
        f'They clicked row {clicked_r}, col {clicked_c}.\n'
        f'Acceptable next opens (any one is a correct logical move): {sol_str}\n'
        f'Teaching pattern hint for you: {teacher_note}\n\n'
        f'Write 2–4 clear sentences in {lang}. Explain briefly what went wrong and '
        f'which type of cell they should have opened instead (reference the visible '
        f'numbers/flags). You may mention row,col for clarity. No Markdown.'
    )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_id)
        resp = model.generate_content(
            prompt,
            generation_config={
                'max_output_tokens': 256,
                'temperature': 0.35,
            },
        )
        text = _response_text(resp)
        return text[:1200] if text else ''
    except Exception:
        return ''
