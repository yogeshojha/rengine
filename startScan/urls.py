from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name="start_scan"),
    path('history/', views.scan_history, name="scan_history"),
]
