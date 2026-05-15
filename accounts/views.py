from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib import messages
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect

from .forms import SignupForm, LoginForm

User = get_user_model()


def home_view(request):
    if request.user.is_authenticated:
        return redirect('game:index')
    return render(request, 'home_guest.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('game:index')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _('Аккаунт создан. Добро пожаловать!'))
            return redirect('game:index')
    else:
        form = SignupForm()

    return render(request, 'registration/register.html', {'form': form})


@csrf_protect
@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('game:index')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            login_value = form.cleaned_data['login'].strip()
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data.get('remember_me', True)

            user = None
            if '@' in login_value:
                user = User.objects.filter(email__iexact=login_value).first()
                if user:
                    user = authenticate(request, username=user.username, password=password)
            if user is None:
                user = authenticate(request, username=login_value, password=password)

            if user is not None:
                login(request, user)
                if not remember_me:
                    request.session.set_expiry(0)
                messages.success(request, _('Вы вошли в аккаунт.'))
                next_url = request.POST.get('next') or request.GET.get('next') or '/'
                return redirect(next_url)
            else:
                messages.error(request, _('Неверное имя пользователя или пароль.'))
        else:
            messages.error(request, _('Исправьте ошибки ниже.'))
    else:
        form = LoginForm()

    next_url = request.GET.get('next') or request.POST.get('next') or '/'
    return render(request, 'registration/login.html', {'form': form, 'next_url': next_url})


@require_http_methods(['GET', 'POST'])
def logout_view(request):
    logout(request)
    messages.success(request, _('Вы вышли из аккаунта.'))
    return redirect('home')


def google_login(request):
    return redirect('/accounts/google/login/')
