import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_GET

from . import engine
from .models import GameResult

def index(request):
    return render(request, 'game/index.html')

@require_POST
def api_new_game(request):
    data = json.loads(request.body)
    difficulty = data.get('difficulty', 'beginner')
    rows = data.get('rows')
    cols = data.get('cols')
    mines = data.get('mines')
    mode = data.get('mode', 'classic')

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

    #chord norm
    if state['revealed'][row][col] and state['board'][row][col] > 0:
        state = engine.chord(state, row, col)
    else:
        state = engine.reveal(state, row, col)

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

@require_POST
def api_save_result(request):
    state = request.session.get('game')
    if not state or state['status'] not in ('won', 'lost'):
        return JsonResponse({'error': 'No finished game'}, status=400)

    data = json.loads(request.body)
    player_name = data.get('name', 'Аноним')[:50]
    elapsed = engine.get_elapsed(state)

    user = request.user if request.user.is_authenticated else None

    result = GameResult.objects.create(
        user=user,
        player_name=player_name,
        difficulty=state['difficulty'],
        rows=state['rows'],
        cols=state['cols'],
        mines=state['mines'],
        result=state['status'],
        time_seconds=elapsed,
    )

    if user:
        _update_profile_stats(user, state, elapsed)

    return JsonResponse({'id': result.id, 'saved': True})


def _update_profile_stats(user, state, elapsed):
    from profiles.models import UserProfile
    profile, _created = UserProfile.objects.get_or_create(user=user)

    profile.games_played += 1
    fields = ['games_played']

    if state['status'] == 'won':
        profile.games_won += 1
        fields.append('games_won')

        diff = state['difficulty']
        best_field = {
            'beginner': 'best_time_beginner',
            'intermediate': 'best_time_intermediate',
            'expert': 'best_time_expert',
        }.get(diff)

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
        difficulty=difficulty, result='win'
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