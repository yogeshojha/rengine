from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
   openapi.Info(
      title="reNgine API",
      default_version='v1',
      description="reNgine: An Automated reconnaissance framework.",
      contact=openapi.Contact(email="yogesh.ojha11@gmail.com"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
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
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + \
    static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
