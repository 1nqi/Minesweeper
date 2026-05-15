from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

from accounts.views import home_view
from game.views_leaderboard import leaderboard as leaderboard_view
from membership import views as membership_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', home_view, name='home'),
    path('', include('accounts.urls')),
    path('', include('profiles.urls')),
    path('play/', include('game.urls')),
    # Явный маршрут до include — надёжный reverse для dev-кнопки (избегает NoReverseMatch)
    path(
        'membership/test-pro-off/',
        membership_views.test_deactivate_pro,
        name='membership_test_pro_off',
    ),
    path('membership/', include('membership.urls')),
    path('leaderboard/', leaderboard_view, name='leaderboard'),
    path('i18n/', include('django.conf.urls.i18n')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
