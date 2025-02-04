from dashboard.models import UserPreferences

from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.urls import resolve
from rest_framework import viewsets
from rest_framework.views import APIView
from knox.auth import TokenAuthentication

import re
from django.conf import settings


IGNORE_PATHS = [re.compile(url) for url in getattr(settings, "LOGIN_REQUIRED_IGNORE_PATHS", [])]

IGNORE_VIEW_NAMES = [name for name in getattr(settings, "LOGIN_REQUIRED_IGNORE_VIEW_NAMES", [])]


class UserPreferencesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user_preferences, created = UserPreferences.objects.get_or_create(
                user=request.user
            )
        return self.get_response(request)


class LoginRequiredMiddleware(AuthenticationMiddleware):
    def _login_required(self, request):
        if request.user.is_authenticated:
            return None

        path = request.path
        if any(url.match(path) for url in IGNORE_PATHS):
            return None

        try:
            resolver = resolve(path)
        except Http404:
            return redirect_to_login(path)

        view_func = resolver.func

        # Extract view class correctly
        view_class = None
        if hasattr(view_func, "cls"):  # DRF ViewSets store their class here
            view_class = view_func.cls
        elif hasattr(view_func, "view_class"):  # Regular CBVs store it here
            view_class = view_func.view_class

        if (
            view_class
            and isinstance(view_class, type)
            and (
                issubclass(view_class, APIView)
                or issubclass(view_class, viewsets.GenericViewSet)
                or issubclass(view_class, viewsets.ViewSet)
            )
        ):
            authentication_classes = getattr(view_class, "authentication_classes", [])
            if TokenAuthentication in authentication_classes:
                return None  # Skip login check for TokenAuthentication views

        if not getattr(view_func, "login_required", True):
            return None

        if view_class and not getattr(view_class, "login_required", True):
            return None

        if resolver.view_name in IGNORE_VIEW_NAMES:
            return None

        return redirect_to_login(path)

    def __call__(self, request):
        response = self._login_required(request)
        if response:
            return response

        return self.get_response(request)
