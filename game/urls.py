from django.urls import path
from . import views

app_name = 'game'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/new/', views.api_new_game, name='api_new'),
    path('api/reveal/', views.api_reveal, name='api_reveal'),
    path('api/flag/', views.api_flag, name='api_flag'),
    path('api/state/', views.api_state, name='api_state'),
    path('api/save/', views.api_save_result, name='api_save'),
    path('api/leaderboard/', views.api_leaderboard, name='api_leaderboard'),
]
