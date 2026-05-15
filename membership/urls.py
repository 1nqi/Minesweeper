from django.urls import path

from . import views

app_name = 'membership'

urlpatterns = [
    path('', views.membership_plans, name='plans'),
    path('checkout/', views.checkout, name='checkout'),
    path('success/', views.success, name='success'),
    path('canceled/', views.canceled, name='canceled'),
    path('webhook/', views.stripe_webhook, name='webhook'),
    path('test-pro/', views.test_activate_pro, name='test_pro'),
]
