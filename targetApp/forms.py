from django import forms
from .models import Domain

class AddDomainForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ['domain_name', 'domain_description']

class RawDomainForm(forms.Form):
    domain_name = forms.CharField(
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
