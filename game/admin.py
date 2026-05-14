from django.contrib import admin
from .models import GameResult


@admin.register(GameResult)
class GameResultAdmin(admin.ModelAdmin):
    list_display = ('player_name', 'difficulty', 'result', 'time_seconds', 'rows', 'cols', 'mines', 'created_at')
    list_filter = ('difficulty', 'result')
    ordering = ('time_seconds',)
