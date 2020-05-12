from django import forms
from scanEngine.models import EngineType

class AddEngineForm(forms.ModelForm):
    class Meta:
        model = EngineType
        fields = []
