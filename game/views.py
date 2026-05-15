import json
import random

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required

from django.utils.translation import get_language

from . import engine
from .gemini_hint import gemini_explain_hint
from .models import GameResult

RANKED_MODES = ('classic', 'speed')


def index(request):
    gemini_on = bool((getattr(settings, 'GEMINI_API_KEY', '') or '').strip()) and getattr(
        settings, 'GEMINI_HINT_EXPLAIN', True
    )
    return render(request, 'game/index.html', {'gemini_hint_enabled': gemini_on})


def _user_is_pro(user):
    if not user.is_authenticated:
        return False
    from profiles.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.is_pro


@require_POST
def api_new_game(request):
    data = json.loads(request.body)
    difficulty = data.get('difficulty', 'beginner')
    rows = data.get('rows')
    cols = data.get('cols')
    mines = data.get('mines')
    mode = data.get('mode', 'classic')

    if not _user_is_pro(request.user) and mode not in ('classic', 'speed'):
        mode = 'classic'

    state = engine.create_game(difficulty, rows, cols, mines, mode=mode)
    request.session['game'] = state
    return JsonResponse(engine.get_client_state(state))


@require_POST
def api_reveal(request):
    state = request.session.get('game')
    if not state:
        return JsonResponse({'error': 'No active game'}, status=400)

    data = json.loads(request.body)
    row, col = data['row'], data['col']

    if state['revealed'][row][col] and state['board'][row][col] > 0:
        state = engine.chord(state, row, col)
    else:
        state = engine.reveal(state, row, col)

    _auto_save_if_finished(request, state)

    request.session['game'] = state
    request.session.modified = True
    return JsonResponse(engine.get_client_state(state))


@require_POST
def api_flag(request):
    state = request.session.get('game')
    if not state:
        return JsonResponse({'error': 'No active game'}, status=400)

    data = json.loads(request.body)
    row, col = data['row'], data['col']
    state = engine.toggle_flag(state, row, col)
    request.session['game'] = state
    request.session.modified = True
    return JsonResponse(engine.get_client_state(state))


@require_GET
def api_state(request):
    state = request.session.get('game')
    if not state:
        state = engine.create_game('beginner')
        request.session['game'] = state
    return JsonResponse(engine.get_client_state(state))


@login_required
@require_GET
def api_ai_status(request):
    from profiles.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    today = timezone.now().date()
    if profile.is_pro:
        return JsonResponse({
            'is_pro': True,
            'remaining': None,
            'unlimited': True,
        })
    used = 0
    if profile.ai_assist_date == today:
        used = profile.ai_assist_count
    return JsonResponse({
        'is_pro': False,
        'remaining': max(0, 3 - used),
        'unlimited': False,
    })


def _pick_safe_hint(state):
    rows, cols = state['rows'], state['cols']
    safe = []
    for r in range(rows):
        for c in range(cols):
            if state['flagged'][r][c] or state['revealed'][r][c]:
                continue
            if state['mines_placed'] and state['mine_map'][r][c]:
                continue
            safe.append((r, c))
    if not safe:
        return None, None
    return random.choice(safe)


@login_required
@require_POST
def api_ai_hint(request):
    state = request.session.get('game')
    if not state or state['status'] in ('won', 'lost'):
        return JsonResponse({'error': 'no_game'}, status=400)

    from profiles.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    today = timezone.now().date()

    if profile.is_pro:
        remaining_after = None
    else:
        if profile.ai_assist_date != today:
            profile.ai_assist_date = today
            profile.ai_assist_count = 0
        if profile.ai_assist_count >= 3:
            return JsonResponse({
                'error': 'limit',
                'remaining': 0,
                'message': 'daily_limit',
            }, status=429)
        remaining_after = 3 - profile.ai_assist_count - 1

    r, c = _pick_safe_hint(state)
    if r is None:
        return JsonResponse({'error': 'no_hint'}, status=400)

    if not profile.is_pro:
        profile.ai_assist_count += 1
        profile.save(update_fields=['ai_assist_date', 'ai_assist_count'])

    message = gemini_explain_hint(state, r, c, get_language() or 'en')

    return JsonResponse({
        'row': r,
        'col': c,
        'remaining': remaining_after,
        'unlimited': profile.is_pro,
        'message': message,
    })


@require_POST
def api_save_result(request):
    state = request.session.get('game')
    if not state or state['status'] not in ('won', 'lost'):
        return JsonResponse({'error': 'No finished game'}, status=400)

    data = json.loads(request.body)
    player_name = (data.get('name') or 'Аноним')[:50]

    result_id = state.get('result_id')
    if result_id:
        GameResult.objects.filter(id=result_id).update(player_name=player_name)
        return JsonResponse({'id': result_id, 'saved': True, 'updated': True})

    _auto_save_if_finished(request, state, force=True, player_name=player_name)
    request.session['game'] = state
    return JsonResponse({'id': state.get('result_id'), 'saved': True})


def _auto_save_if_finished(request, state, force=False, player_name=None):
    if state.get('status') not in ('won', 'lost'):
        return
    if state.get('result_id') and not force:
        return

    user = request.user if request.user.is_authenticated else None
    name = player_name or (user.username if user else 'Аноним')
    elapsed = engine.get_elapsed(state)

    result = GameResult.objects.create(
        user=user,
        player_name=name[:50],
        difficulty=state['difficulty'],
        mode=state.get('mode', 'classic'),
        rows=state['rows'],
        cols=state['cols'],
        mines=state['mines'],
        result=state['status'],
        time_seconds=elapsed,
    )
    state['result_id'] = result.id

    if user:
        _update_profile_stats(user, state, elapsed)


def _update_profile_stats(user, state, elapsed):
    from profiles.models import UserProfile
    profile, _created = UserProfile.objects.get_or_create(user=user)

    profile.games_played += 1
    fields = ['games_played']

    if state['status'] == 'won':
        profile.games_won += 1
        fields.append('games_won')

        if state.get('mode', 'classic') in RANKED_MODES:
            best_field = {
                'beginner': 'best_time_beginner',
                'intermediate': 'best_time_intermediate',
                'expert': 'best_time_expert',
            }.get(state['difficulty'])
            if best_field:
                current_best = getattr(profile, best_field)
                if current_best is None or elapsed < current_best:
                    setattr(profile, best_field, elapsed)
                    fields.append(best_field)

    profile.save(update_fields=fields)


@require_GET
def api_leaderboard(request):
    difficulty = request.GET.get('difficulty', 'beginner')
    results = GameResult.objects.filter(
        difficulty=difficulty, result='win', mode__in=RANKED_MODES
    ).order_by('time_seconds')[:20]

    data = [
        {
            'name': r.player_name,
            'time': r.time_seconds,
            'date': r.created_at.strftime('%d.%m.%Y'),
        }
        for r in results
    ]
    return JsonResponse({'leaderboard': data})
