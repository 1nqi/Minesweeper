from django.conf import settings


def google_oauth(request):
    cid = (getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None) or '').strip()
    sec = (getattr(settings, 'GOOGLE_OAUTH_SECRET', None) or '').strip()
    return {'google_oauth_configured': bool(cid and sec)}
