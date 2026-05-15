from django import forms
from django.utils.translation import gettext_lazy as _
from .models import UserProfile
from .countries import COUNTRY_CHOICES

FLAIR_CATEGORIES = [
    ('Membership', [
        '💎', '🔷', '🔮', '❤️', '🔶', '💗', '🩶', '🪩',
        '👑', '👸', '🤴', '💛', '🧡', '❤️‍🔥', '🖤', '💜',
        '⭐', '🌟', '✨', '💫', '🌠', '⚜️', '🏅', '🎖️',
    ]),
    ('Emoji', [
        '😀', '😎', '🤩', '😏', '🙂', '😃', '😁', '😬',
        '🤓', '😡', '😤', '😢', '💀', '🤑', '😂', '🤭',
        '🥳', '🫡', '👏', '🤝', '🙌', '😇', '🥶', '🫠',
    ]),
    ('Minesweeper', [
        '💣', '🚩', '🏆', '🔥', '⚡', '🎯', '🧠', '🗺️',
        '💥', '🛡️', '⏱️', '🎰', '🧨', '🪖', '🏴‍☠️', '🔍',
    ]),
]

FLAIR_EMOJI_CHOICES = [('', 'Нет')]
for _cat, _items in FLAIR_CATEGORIES:
    FLAIR_EMOJI_CHOICES.extend([(e, e) for e in _items])


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['display_name', 'status', 'bio', 'flair_emoji', 'country', 'language', 'avatar']
        widgets = {
            'display_name': forms.TextInput(attrs={
                'class': 'profile-form__input',
                'placeholder': _('Отображаемое имя'),
                'maxlength': 50,
            }),
            'status': forms.TextInput(attrs={
                'class': 'profile-form__input',
                'placeholder': _('Короткий статус'),
                'maxlength': 120,
            }),
            'bio': forms.Textarea(attrs={
                'class': 'profile-form__textarea',
                'rows': 3,
                'placeholder': _('Расскажите о себе'),
                'maxlength': 200,
            }),
            'flair_emoji': forms.HiddenInput(attrs={'id': 'id_flair_emoji'}),
            'country': forms.Select(attrs={
                'class': 'profile-form__input',
            }),
            'language': forms.Select(attrs={
                'class': 'profile-form__input',
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'profile-form__file',
                'accept': 'image/jpeg,image/png,image/webp,image/gif',
            }),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'size') and avatar.size > 5 * 1024 * 1024:
            raise forms.ValidationError(_('Изображение должно быть меньше 5 МБ.'))
        return avatar
