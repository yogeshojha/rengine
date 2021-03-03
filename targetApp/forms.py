from django import forms
from .models import Domain
from reNgine.validators import validate_domain


class AddTargetForm(forms.Form):
    domain_name = forms.CharField(
        validators=[validate_domain],
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "domainName",
                "placeholder": "example.com"
            }
        ))
    domain_description = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "domainDescription",
            }
        ))

    def clean_domain_name(self):
        data = self.cleaned_data['domain_name']
        if Domain.objects.filter(domain_name=data).count() > 0:
            raise forms.ValidationError("{} target/domain already exists".format(data))
        return data


class UpdateTargetForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ['domain_name', 'domain_description']
    domain_name = forms.CharField(
        validators=[validate_domain],
        required=True,
        disabled=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "domainName",
            }
        ))
    domain_description = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "domainDescription",
            }
        ))

    def set_value(self, domain_value, domain_description_value):
        self.initial['domain_name'] = domain_value
        self.initial['domain_description'] = domain_description_value
