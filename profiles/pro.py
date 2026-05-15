"""Что доступно без Pro — flair и темы."""

from .flair_catalog import FLAIR_EMOJIS_PRO_ONLY

THEMES_FREE = frozenset({'classic', 'ocean'})


def flair_allowed_for_user(emoji: str, is_pro: bool) -> bool:
    if is_pro:
        return True
    if not emoji:
        return True
    return emoji not in FLAIR_EMOJIS_PRO_ONLY


def theme_allowed_for_user(theme: str, is_pro: bool) -> bool:
    if is_pro:
        return True
    return theme in THEMES_FREE
