from django.shortcuts import render
from django.db.models import Min, Count
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import GameResult
from profiles.models import UserProfile
from profiles.countries import COUNTRY_CHOICES

User = get_user_model()

DIFFICULTIES = ['beginner', 'intermediate', 'expert']
DIFF_LABELS = {
    'beginner': _('Новичок'),
    'intermediate': _('Любитель'),
    'expert': _('Эксперт'),
}

RANKED_MODES = ('classic', 'speed')

COUNTRY_NAMES = {code: name for code, name in COUNTRY_CHOICES if code}


def leaderboard(request):
    difficulty = request.GET.get('difficulty', 'beginner')
    if difficulty not in DIFFICULTIES:
        difficulty = 'beginner'

    view = request.GET.get('view', 'players')
    if view not in ('players', 'countries'):
        view = 'players'

    country = request.GET.get('country', '')

    base_qs = GameResult.objects.filter(
        difficulty=difficulty, result='win',
        mode__in=RANKED_MODES, user__isnull=False,
    ).select_related('user')

    countries_with_results = (
        UserProfile.objects
        .filter(country__gt='', user__game_results__result='win',
                user__game_results__mode__in=RANKED_MODES,
                user__game_results__difficulty=difficulty)
        .values_list('country', flat=True)
        .distinct()
    )
    country_set = set(countries_with_results)
    available_countries = [
        (code, name) for code, name in COUNTRY_CHOICES
        if code and code in country_set
    ]

    if view == 'countries':
        country_rows = _country_rankings(difficulty)
        return render(request, 'game/leaderboard.html', {
            'view': view,
            'difficulty': difficulty,
            'current_country': '',
            'difficulties': [(d, DIFF_LABELS[d]) for d in DIFFICULTIES],
            'available_countries': available_countries,
            'country_rows': country_rows,
            'rows': [],
        })

    if country:
        user_ids = UserProfile.objects.filter(country=country).values_list('user_id', flat=True)
        base_qs = base_qs.filter(user_id__in=user_ids)

    best_per_user = (
        base_qs
        .values('user_id')
        .annotate(best_time=Min('time_seconds'))
        .order_by('best_time')[:50]
    )

    user_ids_ordered = [row['user_id'] for row in best_per_user]
    times_map = {row['user_id']: row['best_time'] for row in best_per_user}

    users = {u.id: u for u in User.objects.filter(id__in=user_ids_ordered)}
    profiles = {
        p.user_id: p
        for p in UserProfile.objects.filter(user_id__in=user_ids_ordered)
    }

    rows = []
    for uid in user_ids_ordered:
        user = users.get(uid)
        profile = profiles.get(uid)
        if not user:
            continue
        rows.append({
            'rank': len(rows) + 1,
            'user': user,
            'profile': profile,
            'country': profile.country if profile else '',
            'time': times_map[uid],
        })

    return render(request, 'game/leaderboard.html', {
        'view': view,
        'rows': rows,
        'difficulty': difficulty,
        'current_country': country,
        'difficulties': [(d, DIFF_LABELS[d]) for d in DIFFICULTIES],
        'available_countries': available_countries,
    })


def _country_rankings(difficulty):
    qs = (
        GameResult.objects
        .filter(difficulty=difficulty, result='win',
                mode__in=RANKED_MODES,
                user__isnull=False, user__profile__country__gt='')
        .values('user__profile__country')
        .annotate(
            best_time=Min('time_seconds'),
            wins=Count('id'),
            players=Count('user_id', distinct=True),
        )
        .order_by('best_time')
    )

    rows = []
    for i, row in enumerate(qs, start=1):
        code = row['user__profile__country']
        rows.append({
            'rank': i,
            'country': code,
            'country_name': COUNTRY_NAMES.get(code, code),
            'best_time': row['best_time'],
            'wins': row['wins'],
            'players': row['players'],
        })
    return rows
