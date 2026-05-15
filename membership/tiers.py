from django.utils.translation import gettext_lazy as _


#REDO REDO
FEATURES = [
    {'key': 'all_themes',   'label': _('Все темы доски'),              'tiers': ['gold', 'platinum', 'diamond']},
    {'key': 'pro_badge',    'label': _('Бейдж Pro в профиле'),         'tiers': ['gold', 'platinum', 'diamond']},
    {'key': 'all_flairs',   'label': _('Все flair-эмодзи'),            'tiers': ['gold', 'platinum', 'diamond']},
    {'key': 'extra_stats',  'label': _('Расширенная статистика'),      'tiers': ['platinum', 'diamond']},
    {'key': 'history',      'label': _('Полная история игр'),          'tiers': ['platinum', 'diamond']},
    {'key': 'animated_avatar', 'label': _('Анимированная рамка аватара'), 'tiers': ['diamond']},
    {'key': 'custom_modes', 'label': _('Доступ ко всем игровым режимам'), 'tiers': ['gold', 'platinum', 'diamond']},
    {'key': 'priority',     'label': _('Приоритет в рекордах'),        'tiers': ['diamond']},
]


TIERS = [
    {
        'key': 'gold',
        'label': 'Gold',
        'emoji': '⭐',
        'color': '#f4c430',
        'monthly_cents': 200,
        'yearly_cents': 2000,
        'tagline': _('Старт в Pro'),
    },
    {
        'key': 'platinum',
        'label': 'Platinum',
        'emoji': '👑',
        'color': '#9aa5b1',
        'monthly_cents': 500,
        'yearly_cents': 5000,
        'tagline': _('Серьёзный игрок'),
    },
    {
        'key': 'diamond',
        'label': 'Diamond',
        'emoji': '💎',
        'color': '#60a5fa',
        'monthly_cents': 1000,
        'yearly_cents': 10000,
        'tagline': _('Все возможности'),
        'popular': True,
    },
]


def get_tier(key):
    for t in TIERS:
        if t['key'] == key:
            return t
    return None


def tier_features(tier_key):
    return [f for f in FEATURES if tier_key in f['tiers']]
