from django import forms
from scanEngine.models import EngineType
from django_ace import AceWidget

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
        required=False,
        widget=forms.CheckboxInput(attrs={"checked": ""}))
    dir_file_search = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={}))
    subdomain_takeover = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={}))
    port_scan = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"checked":""}))
    fetch_url = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"checked":""}))
    yaml_configuration = forms.CharField(widget=AceWidget(
        mode="yaml",
        theme="monokai",
        width="100%",
        height="650px",
        minlines=45,
        maxlines='Infinity',
        tabsize=4,
        fontsize=13,
        toolbar=True,))
