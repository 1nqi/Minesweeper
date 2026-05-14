from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta

ONLINE_WINDOW = timedelta(minutes=5)


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    display_name = models.CharField(max_length=50, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, max_length=200)
    status = models.CharField(max_length=120, blank=True)
    flair_emoji = models.CharField(max_length=16, blank=True)

    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(blank=True, null=True)

    games_played = models.PositiveIntegerField(default=0)
    games_won = models.PositiveIntegerField(default=0)
    best_time_beginner = models.FloatField(null=True, blank=True)
    best_time_intermediate = models.FloatField(null=True, blank=True)
    best_time_expert = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Profile: {self.user.username}"

    @property
    def display_username(self):
        return self.display_name.strip() or self.user.username

    @property
    def win_rate(self):
        if self.games_played == 0:
            return 0
        return round(100 * self.games_won / self.games_played, 1)

    @property
    def is_online_now(self):
        if not self.last_seen or not self.is_online:
            return False
        return timezone.now() - self.last_seen <= ONLINE_WINDOW
