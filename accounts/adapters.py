"""django-allauth: связывание Google-аккаунта с уже существующим пользователем по email."""

from __future__ import annotations

from django.contrib.auth import get_user_model

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

User = get_user_model()


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Если в базе уже есть пользователь с таким же email (регистрация по паролю),
        подключаем к нему соцаккаунт вместо ошибки «email уже занят».
        """
        if sociallogin.is_existing:
            return

        email = (sociallogin.account.extra_data or {}).get('email')
        if not email:
            return
        email = str(email).strip().lower()
        if not email:
            return
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return
        sociallogin.connect(request, user)
