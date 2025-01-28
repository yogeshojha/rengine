from django.conf import settings

from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from rest_framework import routers
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

# from reNgine.views import serve_protected_media

router = routers.DefaultRouter()

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path(
        'admin/',
        admin.site.urls),
    path(
        '',
        include('dashboard.urls')),
    path(
        'target/',
        include('targetApp.urls')),
    path(
        'scanEngine/',
        include('scanEngine.urls')),
    path(
        'scan/',
        include('startScan.urls')),
    path(
        'recon_note/',
        include('recon_note.urls')),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='base/login.html'),
        name='login'),
    path(
        'logout/',
        auth_views.LogoutView.as_view(template_name='base/logout.html'),
        name='logout'),
    path(
        'api/',
        include(
            'api.urls',
            'api')),
    path(r"api/auth/", include("knox.urls")),
    # path(
    #     'media/<path:path>',
    #     serve_protected_media,
    #     name='serve_protected_media'
    # ),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# ] + static(settings.MEDIA_URL, document_root=settings.RENGINE_RESULTS) + \
