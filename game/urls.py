from django.urls import path
from . import views
from . import puzzle_views

app_name = 'game'

urlpatterns = [
    path('', views.index, name='index'),
    path('puzzles/', puzzle_views.puzzles_list, name='puzzles'),
    path('puzzles/<int:puzzle_id>/', puzzle_views.puzzle_play, name='puzzle_play'),
    path('api/puzzle/reveal/', puzzle_views.api_puzzle_reveal, name='api_puzzle_reveal'),
    path('api/puzzle/reset/', puzzle_views.api_puzzle_reset, name='api_puzzle_reset'),
    path('api/new/', views.api_new_game, name='api_new'),
    path('api/reveal/', views.api_reveal, name='api_reveal'),
    path('api/flag/', views.api_flag, name='api_flag'),
    path('api/state/', views.api_state, name='api_state'),
    path('api/save/', views.api_save_result, name='api_save'),
    path('api/leaderboard/', views.api_leaderboard, name='api_leaderboard'),
    path('api/ai-status/', views.api_ai_status, name='api_ai_status'),
    path('api/hint/', views.api_ai_hint, name='api_ai_hint'),
]
