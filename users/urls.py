"""Define patrones de URL para Users"""
from django.urls import path, include
from . import views

app_name = 'users'
urlpatterns = [
    #Incluye url de autenticación predeterminadas.
    path('', include('django.contrib.auth.urls')),
    path('register/', views.register, name='register'),
]
