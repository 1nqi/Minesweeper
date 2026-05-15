import copy
import json
import time

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import get_language
from django.views.decorators.http import require_POST

from profiles.puzzle_ai_quota import (
    puzzle_ai_can_use_gemini,
    puzzle_ai_consume_on_successful_explanation,
    puzzle_ai_quota_for_request,
)

from .engine import _check_win, _flood_fill, get_client_state
from .gemini_hint import gemini_explain_puzzle_mistake
from .puzzle_catalog import all_puzzle_specs, build_puzzle_state, get_puzzle_spec

SESSION_PROGRESS = 'puzzle_progress'
SESSION_PUZZLE_STATE = 'puzzle_state'


def _puzzle_state_for_session(state: dict) -> dict:
    """Session backends use JSON by default — frozenset is not serializable."""
    st = copy.deepcopy(state)
    sc = st.get('solution_cells')
    if isinstance(sc, (frozenset, set)):
        st['solution_cells'] = [list(t) for t in sc]
    return st


def _ensure_puzzle_state_from_session(state: dict) -> None:
    sc = state.get('solution_cells')
    if isinstance(sc, list):
        state['solution_cells'] = frozenset(
            tuple(x) if isinstance(x, (list, tuple)) else x for x in sc
        )


def _save_puzzle_session(request, state: dict) -> None:
    request.session[SESSION_PUZZLE_STATE] = _puzzle_state_for_session(state)
    request.session.modified = True


def _json_sanitize(obj):
    """Make structures JSON-serializable (frozenset / tuple / nested)."""
    if isinstance(obj, dict):
        return {k: _json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_sanitize(v) for v in obj]
    if isinstance(obj, (frozenset, set)):
        return [_json_sanitize(v) for v in obj]
    return obj


def _progress(request):
    raw = request.session.get(SESSION_PROGRESS) or {}
    solved = set(raw.get('solved', []))
    top_id = max(p['id'] for p in all_puzzle_specs())
    max_unlocked = max(1, int(raw.get('max_unlocked', 1)))
    max_unlocked = min(max_unlocked, top_id + 1)
    return solved, max_unlocked


def _save_progress(request, solved: set[int], max_unlocked: int):
    request.session[SESSION_PROGRESS] = {
        'solved': list(solved),
        'max_unlocked': max_unlocked,
    }
    request.session.modified = True


def record_puzzle_solved(request, puzzle_id: int):
    solved, mu = _progress(request)
    solved.add(puzzle_id)
    mu = max(mu, puzzle_id + 1)
    top_id = max(p['id'] for p in all_puzzle_specs())
    mu = min(mu, top_id + 1)
    _save_progress(request, solved, mu)


def _puzzle_ai_attach_quota(out: dict, request) -> None:
    q = puzzle_ai_quota_for_request(request)
    out['puzzle_ai_unlimited'] = q['unlimited']
    out['puzzle_ai_remaining'] = q['remaining']
    out['puzzle_ai_membership_url'] = reverse('membership:plans')


def _puzzle_fail_explanation(
    request,
    snap: dict,
    *,
    puzzle_id: int,
    row: int,
    col: int,
    kind: str,
    solutions: frozenset,
    teacher: str,
    lang: str,
    fallback: str,
) -> str:
    if puzzle_ai_can_use_gemini(request):
        explanation = gemini_explain_puzzle_mistake(
            snap,
            puzzle_id=puzzle_id,
            clicked_r=row,
            clicked_c=col,
            kind=kind,
            solution_cells=solutions,
            teacher_note=teacher,
            language_code=lang,
        )
        if explanation.strip():
            puzzle_ai_consume_on_successful_explanation(request)
            return explanation.strip()
        return fallback

    if not puzzle_ai_quota_for_request(request)['unlimited']:
        return fallback + ' ' + str(_(
            'Лимит ИИ-объяснений к пазлам на сегодня исчерпан (3 для бесплатных аккаунтов). '
            'Оформите Pro для безлимита или вернитесь завтра.'
        ))
    return fallback


def puzzles_list(request):
    solved, max_unlocked = _progress(request)
    puzzles = []
    for spec in all_puzzle_specs():
        pid = spec['id']
        puzzles.append({
            'spec': spec,
            'locked': pid > max_unlocked,
            'done': pid in solved,
        })
    return render(request, 'game/puzzles.html', {
        'puzzles': puzzles,
        'solved_count': len(solved),
        'max_unlocked': max_unlocked,
    })


def puzzle_play(request, puzzle_id: int):
    spec = get_puzzle_spec(puzzle_id)
    if not spec:
        messages.error(request, _('Пазл не найден.'))
        return redirect('game:puzzles')
    _solved, max_unlocked = _progress(request)
    if puzzle_id > max_unlocked:
        messages.warning(request, _('Сначала пройдите предыдущие пазлы.'))
        return redirect('game:puzzles')

    state = build_puzzle_state(puzzle_id)
    if not state:
        return redirect('game:puzzles')
    _save_puzzle_session(request, state)

    initial = get_client_state(state)
    q = puzzle_ai_quota_for_request(request)
    return render(request, 'game/puzzle_play.html', {
        'puzzle_id': puzzle_id,
        'puzzle_spec': spec,
        'initial_state_json': json.dumps(_json_sanitize(initial)),
        'puzzle_ai_unlimited': q['unlimited'],
        'puzzle_ai_remaining': q['remaining'],
    })


def _lose_show_mines(state: dict) -> None:
    state['status'] = 'lost'
    state['end_time'] = time.time()
    for r in range(state['rows']):
        for c in range(state['cols']):
            if state['mine_map'][r][c]:
                state['revealed'][r][c] = True


@require_POST
def api_puzzle_reset(request):
    data = json.loads(request.body or '{}')
    puzzle_id = int(data.get('puzzle_id', 0))
    spec = get_puzzle_spec(puzzle_id)
    if not spec:
        return JsonResponse({'error': 'unknown'}, status=400)
    _solved, max_unlocked = _progress(request)
    if puzzle_id > max_unlocked:
        return JsonResponse({'error': 'locked'}, status=403)
    state = build_puzzle_state(puzzle_id)
    _save_puzzle_session(request, state)
    out = get_client_state(state)
    _puzzle_ai_attach_quota(out, request)
    return JsonResponse(out)


@require_POST
def api_puzzle_reveal(request):
    raw = request.session.get(SESSION_PUZZLE_STATE)
    if not raw or raw.get('mode') != 'puzzle':
        return JsonResponse({'error': 'no_puzzle'}, status=400)
    state = copy.deepcopy(raw)
    _ensure_puzzle_state_from_session(state)
    if state['status'] != 'playing':
        return JsonResponse({'error': 'done'}, status=400)

    data = json.loads(request.body or '{}')
    row, col = int(data['row']), int(data['col'])

    if state['flagged'][row][col]:
        return JsonResponse({'error': 'flagged'}, status=400)
    if state['revealed'][row][col]:
        return JsonResponse({'error': 'revealed'}, status=400)

    snap = copy.deepcopy(state)
    puzzle_id = state['puzzle_id']
    solutions = state['solution_cells']
    if not isinstance(solutions, (set, frozenset)):
        solutions = frozenset(tuple(x) for x in solutions)
    teacher = state.get('teacher_note', '')
    lang = get_language() or 'en'

    if state['mine_map'][row][col]:
        fb = str(_(
            'Это мина. Ориентируйтесь на цифры и флаги и открывайте логически выводимую клетку.'
        ))
        explanation = _puzzle_fail_explanation(
            request, snap,
            puzzle_id=puzzle_id, row=row, col=col, kind='mine',
            solutions=solutions, teacher=teacher, lang=lang, fallback=fb,
        )
        _lose_show_mines(state)
        _save_puzzle_session(request, state)
        out = get_client_state(state)
        out['puzzle_fail'] = True
        out['explanation'] = explanation
        _puzzle_ai_attach_quota(out, request)
        return JsonResponse(out)

    if (row, col) not in solutions:
        fb = str(_(
            'Эта клетка не следует из текущих подсказок однозначно; попробуйте другую.'
        ))
        explanation = _puzzle_fail_explanation(
            request, snap,
            puzzle_id=puzzle_id, row=row, col=col, kind='wrong_safe',
            solutions=solutions, teacher=teacher, lang=lang, fallback=fb,
        )
        state['status'] = 'lost'
        state['end_time'] = time.time()
        _save_puzzle_session(request, state)
        out = get_client_state(state)
        out['puzzle_fail'] = True
        out['explanation'] = explanation
        _puzzle_ai_attach_quota(out, request)
        return JsonResponse(out)

    _flood_fill(state, row, col)
    _check_win(state)
    if state['status'] != 'won':
        state['status'] = 'won'
        state['end_time'] = time.time()
    record_puzzle_solved(request, puzzle_id)
    _save_puzzle_session(request, state)
    return JsonResponse(get_client_state(state))
