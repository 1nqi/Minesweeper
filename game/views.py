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

    state = engine.create_game(difficulty, rows, cols, mines)
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

    result = GameResult.objects.create(
        player_name=player_name,
        difficulty=state['difficulty'],
        rows=state['rows'],
        cols=state['cols'],
        mines=state['mines'],
        result=state['status'],
        time_seconds=engine.get_elapsed(state),
    )

    return JsonResponse({'id': result.id, 'saved': True})

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