from django import forms
from .models import Domain
from .validators import validate_domain

class RawTargetForm(forms.Form):
    domain_name = forms.CharField(
                    validators=[validate_domain],
                    required=True,
                    widget=forms.TextInput(
                        attrs={
                            "class": "form-control",
                            "id": "domainName",
                            "placeholder":"example.com"
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
                
class UpdateTargetForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ['domain_name', 'domain_description']
    domain_name = forms.CharField(
                    validators=[validate_domain],
                    required=True,
                    widget=forms.TextInput(
                        attrs={
                            "class": "form-control",
                            "id": "domainName",
                            "placeholder":"example.com"
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
