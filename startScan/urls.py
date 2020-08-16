from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path(
        '',
        views.index,
        name="start_scan"),
    path(
        'history/',
        views.scan_history,
        name="scan_history"),
    path(
        'scheduled/',
        views.schedule_scan_view,
        name="scheduled_scan"),
    path(
        'detail/<int:id>',
        views.detail_scan,
        name='detail_scan'),
    path(
        'start/<int:host_id>',
        views.start_scan_ui,
        name='start_scan'),
    path(
        'api/',
        include(
            'startScan.api.urls',
            'scan_host_api')),
    path(
        'export/subdomains/<int:scan_id>',
        views.export_subdomains,
        name='export_subdomains'),
    path(
        'export/endpoints/<int:scan_id>',
        views.export_endpoints,
        name='export_endpoints'),
    path(
        'export/urls/<int:scan_id>',
        views.export_urls,
        name='export_http_urls'),
    path(
        'delete/scan/<int:id>',
        views.delete_scan,
        name='delete_scan'),
    path(
        'stop/scan/<str:id>',
        views.stop_scan,
        name='stop_scan'),
    path(
        'delete/scheduled_task/<int:id>',
        views.delete_scheduled_task,
        name='delete_scheduled_task'),
]
