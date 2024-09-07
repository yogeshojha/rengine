from dashboard.models import UserPreferences

class UserPreferencesMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		if request.user.is_authenticated:
			request.user_preferences, created = UserPreferences.objects.get_or_create(user=request.user)
		return self.get_response(request)
