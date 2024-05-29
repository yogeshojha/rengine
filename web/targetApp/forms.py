from django import forms
from reNgine.validators import validate_domain

from .models import *


class AddTargetForm(forms.Form):
    name = forms.CharField(
        validators=[validate_domain],
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "domainName",
                "placeholder": "example.com"
            }
        ))
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "domainDescription",
                "placeholder": "Target Description"
            }
        ))
    h1_team_handle = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg ",
                "id": "h1_team_handle",
                "placeholder": "team_handle"
            }
        ))
    organization_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "organizationName",
                "placeholder": "Organization Name"
            }
        ))

class AddOrganizationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        project = kwargs.pop('project')
        super(AddOrganizationForm, self).__init__(*args, **kwargs)
        self.fields['domains'].choices = [(domain.id, domain.name) for domain in Domain.objects.filter(project__slug=project) if not domain.get_organization()]

    name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "organizationName",
                "placeholder": "Organization Name"
            }
        ))

    description = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "id": "organizationDescription",
            }
        ))

    domains = forms.ChoiceField(
        required=True,
        widget=forms.Select(
            attrs={
                "class": "form-control select2-multiple",
                "multiple": "multiple",
                "data-toggle": "select2",
                "data-width": "100%",
                "multiple": "multiple",
                "data-placeholder": "Choose Targets",
                "id": "domains",
            }
        )
    )

    def clean_name(self):
        data = self.cleaned_data['name']
        if Organization.objects.filter(name=data).count() > 0:
            raise forms.ValidationError(f"{data} Organization already exists")
        return data


class UpdateTargetForm(forms.ModelForm):
    class Meta:
        model = Domain
        fields = ['name', 'description', 'h1_team_handle']
    name = forms.CharField(
        validators=[validate_domain],
        required=True,
        disabled=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "domainName",
            }
        ))
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "domainDescription",
            }
        ))

    h1_team_handle = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "h1_team_handle",
            }
        ))

    def set_value(self, domain_value, description_value, h1_team_handle):
        self.initial['name'] = domain_value
        self.initial['description'] = description_value
        self.initial['h1_team_handle'] = h1_team_handle


class UpdateOrganizationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UpdateOrganizationForm, self).__init__(*args, **kwargs)
        self.fields['domains'].choices = [(domain.id, domain.name) for domain in Domain.objects.all()]

    class Meta:
        model = Organization
        fields = ['name', 'description']

    name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "organizationName",
            }
        ))

    description = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "organizationDescription",
            }
        ))

    domains = forms.ChoiceField(
        required=True,
        widget=forms.Select(
            attrs={
                "class": "form-control form-control-lg tagging",
                "multiple": "multiple",
                "id": "domains",
            }
        )
    )

    def set_value(self, organization_value, description_value):
        self.initial['name'] = organization_value
        self.initial['description'] = description_value
