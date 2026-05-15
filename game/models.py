from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class GameResult(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', _('Новичок')),
        ('intermediate', _('Любитель')),
        ('expert', _('Эксперт')),
        ('custom', _('Свой')),
    ]

    RESULT_CHOICES = [
        ('win', _('Победа')),
        ('loss', _('Поражение')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='game_results',
    )
    player_name = models.CharField(_('Имя игрока'), max_length=50, default=_('Аноним'))
    difficulty = models.CharField(_('Сложность'), max_length=20, choices=DIFFICULTY_CHOICES)
    rows = models.PositiveIntegerField(_('Строки'))
    cols = models.PositiveIntegerField(_('Столбцы'))
    mines = models.PositiveIntegerField(_('Мины'))
    result = models.CharField(_('Результат'), max_length=4, choices=RESULT_CHOICES)
    time_seconds = models.FloatField(_('Время (сек)'))
    created_at = models.DateTimeField(_('Дата'), auto_now_add=True)

    class Meta:
        verbose_name = _('Результат игры')
        verbose_name_plural = _('Результаты игр')
        ordering = ['time_seconds']

    def __str__(self):
        return f"{self.player_name} — {self.get_difficulty_display()} — {self.time_seconds}s"
