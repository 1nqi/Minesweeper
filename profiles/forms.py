from django import forms
from .models import UserProfile

FLAIR_EMOJI_CHOICES = [
    ('', 'Нет'),
    ('😎', '😎'), ('🔥', '🔥'), ('⭐', '⭐'), ('👑', '👑'),
    ('💎', '💎'), ('🏆', '🏆'), ('⚡', '⚡'), ('🧠', '🧠'),
    ('🎯', '🎯'), ('💣', '💣'), ('🚩', '🚩'),
]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['display_name', 'status', 'bio', 'flair_emoji', 'avatar']
        widgets = {
            'display_name': forms.TextInput(attrs={
                'class': 'profile-form__input',
                'placeholder': 'Отображаемое имя',
                'maxlength': 50,
            }),
            'status': forms.TextInput(attrs={
                'class': 'profile-form__input',
                'placeholder': 'Короткий статус',
                'maxlength': 120,
            }),
            'bio': forms.Textarea(attrs={
                'class': 'profile-form__textarea',
                'rows': 3,
                'placeholder': 'Расскажите о себе',
                'maxlength': 200,
            }),
            'flair_emoji': forms.HiddenInput(attrs={'id': 'id_flair_emoji'}),
            'avatar': forms.FileInput(attrs={
                'class': 'profile-form__file',
                'accept': 'image/jpeg,image/png,image/webp,image/gif',
            }),
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'size') and avatar.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Изображение должно быть меньше 5 МБ.')
        return avatar
