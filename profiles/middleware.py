from django.utils import timezone, translation


class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
            except Exception:
                profile = None

            if profile:
                if profile.language:
                    translation.activate(profile.language)
                    request.LANGUAGE_CODE = profile.language

                # обновляем онлайн-статус не чаще раза в минуту
                now = timezone.now()
                if not profile.last_seen or (now - profile.last_seen).total_seconds() > 60:
                    profile.is_online = True
                    profile.last_seen = now
                    profile.save(update_fields=['is_online', 'last_seen'])

        response = self.get_response(request)
        return response
