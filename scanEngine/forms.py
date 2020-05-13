from django import forms
from scanEngine.models import EngineType

class AddEngineForm(forms.ModelForm):
    class Meta:
        model = EngineType
        fields = '__all__'
    scan_type_name = forms.CharField(
                    required=True,
                    widget=forms.TextInput(
                        attrs={
                            "class": "form-control",
                            "id": "scan_engine_name",
                            "placeholder":"Custom Engine"
                        }
                    ))
    subdomain_discovery = forms.BooleanField(
                    required=True,
                    widget=forms.CheckboxInput(attrs={"checked":"", "disabled":""}))
    dir_file_search = forms.BooleanField(
                    required=False,
                    widget=forms.CheckboxInput(attrs={}))
    subdomain_takeover = forms.BooleanField(
                    required=False,
                    widget=forms.CheckboxInput(attrs={}))
    param_discovery = forms.BooleanField(
                    required=False,
                    widget=forms.CheckboxInput(attrs={}))
    port_scan = forms.BooleanField(
                    required=False,
                    widget=forms.CheckboxInput(attrs={"checked":""}))
