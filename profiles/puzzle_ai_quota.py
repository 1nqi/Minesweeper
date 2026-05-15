"""Дневной лимит ИИ-объяснений к пазлам (отдельно от подсказок в игре)."""

from __future__ import annotations

from django.utils import timezone

from .models import UserProfile

PUZZLE_AI_EXPLAIN_DAILY_FREE = 3
SESSION_PUZZLE_AI = 'puzzle_ai_explain'


def _today():
    return timezone.now().date()


def puzzle_ai_quota_for_request(request) -> dict:
    """
    unlimited: True → Pro, безлимит Gemini для пазлов.
    remaining: int — сколько ИИ-объяснений осталось сегодня (0..3); None если unlimited.
    """
    if request.user.is_authenticated:
        profile, _created = UserProfile.objects.get_or_create(user=request.user)
        if profile.is_pro:
            return {'unlimited': True, 'remaining': None}
        today = _today()
        if profile.puzzle_ai_explain_date != today:
            rem = PUZZLE_AI_EXPLAIN_DAILY_FREE
        else:
            rem = max(0, PUZZLE_AI_EXPLAIN_DAILY_FREE - profile.puzzle_ai_explain_count)
        return {'unlimited': False, 'remaining': rem}

    raw = request.session.get(SESSION_PUZZLE_AI) or {}
    d_raw = raw.get('d')
    c = int(raw.get('c', 0))
    today_s = str(_today())
    if d_raw != today_s:
        rem = PUZZLE_AI_EXPLAIN_DAILY_FREE
    else:
        rem = max(0, PUZZLE_AI_EXPLAIN_DAILY_FREE - c)
    return {'unlimited': False, 'remaining': rem}


def puzzle_ai_can_use_gemini(request) -> bool:
    q = puzzle_ai_quota_for_request(request)
    if q['unlimited']:
        return True
    return (q['remaining'] or 0) > 0


def puzzle_ai_consume_on_successful_explanation(request) -> None:
    """Вызывать только после непустого ответа Gemini."""
    if request.user.is_authenticated:
        profile, _created = UserProfile.objects.get_or_create(user=request.user)
        if profile.is_pro:
            return
        today = _today()
        if profile.puzzle_ai_explain_date != today:
            profile.puzzle_ai_explain_date = today
            profile.puzzle_ai_explain_count = 0
        profile.puzzle_ai_explain_count += 1
        profile.save(update_fields=['puzzle_ai_explain_date', 'puzzle_ai_explain_count'])
        return

    today_s = str(_today())
    raw = request.session.get(SESSION_PUZZLE_AI) or {}
    d_raw = raw.get('d')
    c = int(raw.get('c', 0))
    if d_raw != today_s:
        c = 0
    c += 1
    request.session[SESSION_PUZZLE_AI] = {'d': today_s, 'c': c}
    request.session.modified = True
