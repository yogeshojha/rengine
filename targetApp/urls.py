from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.index, name='targetIndex'),
    path('add/', views.addTarget, name='addTarget'),
    path('list/', views.listTarget, name='listTarget'),
]
