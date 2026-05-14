from django.db import models
from django.conf import settings


class GameResult(models.Model):
    DIFFICULTY_CHOICES = [
        ('beginner', 'Новичок'),
        ('intermediate', 'Любитель'),
        ('expert', 'Эксперт'),
        ('custom', 'Свой'),
    ]

    RESULT_CHOICES = [
        ('win', 'Победа'),
        ('loss', 'Поражение'),
    ]

    player_name = models.CharField('Имя игрока', max_length=50, default='Аноним')
    difficulty = models.CharField('Сложность', max_length=20, choices=DIFFICULTY_CHOICES)
    rows = models.PositiveIntegerField('Строки')
    cols = models.PositiveIntegerField('Столбцы')
    mines = models.PositiveIntegerField('Мины')
    result = models.CharField('Результат', max_length=4, choices=RESULT_CHOICES)
    time_seconds = models.FloatField('Время (сек)')
    created_at = models.DateTimeField('Дата', auto_now_add=True)

    class Meta:
        verbose_name = 'Результат игры'
        verbose_name_plural = 'Результаты игр'
        ordering = ['time_seconds']

    def __str__(self):
        return f"{self.player_name} — {self.get_difficulty_display()} — {self.time_seconds}s"
