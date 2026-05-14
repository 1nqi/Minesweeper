from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F
from django.views.decorators.http import require_http_methods

from .models import UserProfile
from .forms import ProfileForm, FLAIR_EMOJI_CHOICES
from game.models import GameResult

User = get_user_model()


def profile_detail(request, username):
    profile_user = get_object_or_404(User, username=username)
    profile, _ = UserProfile.objects.get_or_create(user=profile_user)

    recent_games = GameResult.objects.filter(
        player_name=profile_user.username
    ).order_by('-created_at')[:20]

    is_owner = request.user == profile_user
    flair_choices = [(v, l) for v, l in FLAIR_EMOJI_CHOICES if v]

    return render(request, 'profiles/detail.html', {
        'profile_user': profile_user,
        'profile': profile,
        'recent_games': recent_games,
        'is_owner': is_owner,
        'flair_choices': flair_choices,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def profile_settings(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён.')
            return redirect('profiles:settings')
    else:
        form = ProfileForm(instance=profile)

    flair_choices = [(v, l) for v, l in FLAIR_EMOJI_CHOICES if v]

    return render(request, 'profiles/settings.html', {
        'profile': profile,
        'form': form,
        'flair_choices': flair_choices,
    })
