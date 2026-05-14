from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('member/<str:username>/', views.profile_detail, name='detail'),
    path('settings/profile/', views.profile_settings, name='settings'),
]
