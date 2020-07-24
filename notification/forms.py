from django import forms
from notification.models import NotificationHooks
from reNgine.validators import validate_url


class AddNotificationHooks(forms.ModelForm):
    class Meta:
        model = NotificationHooks
        fields = '__all__'

    hook_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'hookName',
                'placeholder': '#awesome-channel'
            }
        ))

    hook_url = forms.CharField(
        validators=[validate_url],
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'hookUrl',
                'placeholder': 'https://hooks.slack.com/services/T00000000/' +
                               'B00000000/XXXXXXXXXXXXXXXXXXXXXXXX'
            }
        ))

    send_notif = forms.BooleanField(widget=forms.HiddenInput(), initial=True)
