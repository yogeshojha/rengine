from django.forms import ModelForm
from users.models import User


class UserSettingsForm(ModelForm):
    class Meta:
        model = User
        fields = ["language"]