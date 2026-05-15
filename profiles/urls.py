from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('member/<str:username>/', views.profile_detail, name='detail'),
    path('settings/profile/', views.profile_settings, name='settings'),
    path('api/update-flair/', views.api_update_flair, name='api_update_flair'),
    path('api/update-status/', views.api_update_status, name='api_update_status'),
]
