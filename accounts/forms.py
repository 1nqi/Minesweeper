from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class SignupForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Email',
            'autocomplete': 'email',
        }),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'auth-input',
            'placeholder': 'Имя пользователя',
            'autocomplete': 'username',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'auth-input',
            'placeholder': 'Пароль',
            'autocomplete': 'new-password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'auth-input',
            'placeholder': 'Подтвердите пароль',
            'autocomplete': 'new-password',
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Это имя пользователя уже занято.')
        return username


class LoginForm(forms.Form):
    login = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Имя пользователя или email',
            'autocomplete': 'username',
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Пароль',
            'autocomplete': 'current-password',
        }),
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'auth-checkbox'}),
    )
