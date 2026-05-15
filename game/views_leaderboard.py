from django.shortcuts import render
from django.db.models import Min, F, Q
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


def leaderboard(request):
    difficulty = request.GET.get('difficulty', 'beginner')
    if difficulty not in DIFFICULTIES:
        difficulty = 'beginner'

    country = request.GET.get('country', '')

    base_qs = GameResult.objects.filter(
        difficulty=difficulty, result='win', user__isnull=False
    ).select_related('user')

    if country:
        user_ids = UserProfile.objects.filter(
            country=country
        ).values_list('user_id', flat=True)
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

    countries_with_results = (
        UserProfile.objects
        .filter(country__gt='', user__game_results__result='win', user__game_results__difficulty=difficulty)
        .values_list('country', flat=True)
        .distinct()
    )
    country_set = set(countries_with_results)
    available_countries = [
        (code, name) for code, name in COUNTRY_CHOICES
        if code and code in country_set
    ]

    return render(request, 'game/leaderboard.html', {
        'rows': rows,
        'difficulty': difficulty,
        'current_country': country,
        'difficulties': [(d, DIFF_LABELS[d]) for d in DIFFICULTIES],
        'available_countries': available_countries,
    })
