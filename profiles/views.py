import json

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from .models import UserProfile
from .forms import ProfileForm, FLAIR_EMOJI_CHOICES, FLAIR_CATEGORIES
from game.models import GameResult

User = get_user_model()

ALLOWED_FLAIRS = {v for v, _label in FLAIR_EMOJI_CHOICES}


def profile_detail(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile, _created = UserProfile.objects.get_or_create(user=profile_user)

    recent_games = GameResult.objects.filter(
        user=profile_user
    ).order_by('-created_at')[:20]

    losses = max(0, (profile.games_played or 0) - (profile.games_won or 0))

    is_owner = request.user == profile_user
    flair_choices = [(val, label) for val, label in FLAIR_EMOJI_CHOICES if val]

    active_tab = request.GET.get('tab', 'overview')
    if active_tab not in ('overview', 'games', 'stats'):
        active_tab = 'overview'

    return render(request, 'profiles/detail.html', {
        'profile_user': profile_user,
        'profile': profile,
        'recent_games': recent_games,
        'is_owner': is_owner,
        'flair_choices': flair_choices,
        'flair_categories': FLAIR_CATEGORIES,
        'active_tab': active_tab,
        'losses': losses,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def profile_settings(request):
    profile, _created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            # сразу применяем новый язык
            if profile.language:
                translation.activate(profile.language)
                request.session['django_language'] = profile.language
            messages.success(request, _('Профиль обновлён.'))
            return redirect('profiles:settings')
    else:
        form = ProfileForm(instance=profile)

    flair_choices = [(val, label) for val, label in FLAIR_EMOJI_CHOICES if val]

    return render(request, 'profiles/settings.html', {
        'profile': profile,
        'form': form,
        'flair_choices': flair_choices,
        'flair_categories': FLAIR_CATEGORIES,
    })


@login_required
@require_POST
def api_update_flair(request):
    data = json.loads(request.body)
    flair = data.get('flair', '')
    if flair not in ALLOWED_FLAIRS:
        flair = ''
    profile, _created = UserProfile.objects.get_or_create(user=request.user)
    profile.flair_emoji = flair
    profile.save(update_fields=['flair_emoji'])
    return JsonResponse({'ok': True, 'flair': flair})


@login_required
@require_POST
def api_update_status(request):
    data = json.loads(request.body)
    status = data.get('status', '').strip()[:120]
    profile, _created = UserProfile.objects.get_or_create(user=request.user)
    profile.status = status
    profile.save(update_fields=['status'])
    return JsonResponse({'ok': True, 'status': status})
