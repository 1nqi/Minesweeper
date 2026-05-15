from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone
from datetime import timedelta

from .countries import COUNTRY_CHOICES, country_flag

ONLINE_WINDOW = timedelta(minutes=5)

LANGUAGE_CHOICES = [(code, name) for code, name in django_settings.LANGUAGES]


class UserProfile(models.Model):
    user = models.OneToOneField(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    display_name = models.CharField(max_length=50, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, max_length=200)
    status = models.CharField(max_length=120, blank=True)
    flair_emoji = models.CharField(max_length=16, blank=True)
    country = models.CharField(max_length=2, blank=True, choices=COUNTRY_CHOICES)
    language = models.CharField(max_length=10, blank=True, default='ru', choices=LANGUAGE_CHOICES)

    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(blank=True, null=True)

    games_played = models.PositiveIntegerField(default=0)
    games_won = models.PositiveIntegerField(default=0)
    best_time_beginner = models.FloatField(null=True, blank=True)
    best_time_intermediate = models.FloatField(null=True, blank=True)
    best_time_expert = models.FloatField(null=True, blank=True)

    PRO_TIERS = [
        ('', 'Free'),
        ('pro', 'Pro'),
    ]
    pro_tier = models.CharField(max_length=16, blank=True, default='', choices=PRO_TIERS)
    pro_until = models.DateTimeField(blank=True, null=True)
    pro_started_at = models.DateTimeField(blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=64, blank=True)

    ai_assist_date = models.DateField(blank=True, null=True)
    ai_assist_count = models.PositiveSmallIntegerField(default=0)

    puzzle_ai_explain_date = models.DateField(blank=True, null=True)
    puzzle_ai_explain_count = models.PositiveSmallIntegerField(default=0)

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
    def flag_emoji(self):
        return country_flag(self.country)

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

    @property
    def is_pro(self):
        if self.pro_tier != 'pro':
            return False
        if self.pro_until and self.pro_until < timezone.now():
            return False
        return True

    @property
    def pro_tier_label(self):
        return dict(self.PRO_TIERS).get(self.pro_tier, 'Free')
