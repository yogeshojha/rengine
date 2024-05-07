from django.conf import settings as django_settings
from django.contrib.auth import views as auth_views

# Needed only to set the language cookie on login and ignore browser language
class LoginView(auth_views.LoginView):
    def post(self, request, *args, **kwargs):
        response = super().post(self, request, *args, **kwargs)
        if request.user.is_authenticated:
            response.set_cookie(django_settings.LANGUAGE_COOKIE_NAME, request.user.language)
        return response