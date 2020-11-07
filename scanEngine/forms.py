from django import forms
from scanEngine.models import EngineType, Configuration
from django_ace import AceWidget
from reNgine.validators import validate_short_name


class AddEngineForm(forms.ModelForm):
    class Meta:
        model = EngineType
        fields = '__all__'
    engine_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "scan_engine_name",
                "placeholder": "Custom Engine"}))
    subdomain_discovery = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"checked": ""}))
    dir_file_search = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={}))
    port_scan = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"checked": ""}))
    fetch_url = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"checked": ""}))
    vulnerability_scan = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"checked": ""}))
    yaml_configuration = forms.CharField(widget=AceWidget(
        mode="yaml",
        theme="monokai",
        width="100%",
        height="450px",
        tabsize=4,
        fontsize=13,
        toolbar=True,))


class UpdateEngineForm(forms.ModelForm):
    class Meta:
        model = EngineType
        fields = '__all__'
    engine_name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "id": "scan_engine_name",
                "placeholder": "Custom Engine"}))
    subdomain_discovery = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput())
    dir_file_search = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput())
    port_scan = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput())
    fetch_url = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput())
    vulnerability_scan = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput())
    yaml_configuration = forms.CharField(widget=AceWidget(
        mode="yaml",
        theme="monokai",
        width="100%",
        height="450px",
        tabsize=4,
        fontsize=13,
        toolbar=True,))

    def set_value(self, engine):
        self.initial['engine_name'] = engine.engine_name
        self.initial['subdomain_discovery'] = engine.subdomain_discovery
        self.initial['dir_file_search'] = engine.dir_file_search
        self.initial['port_scan'] = engine.port_scan
        self.initial['fetch_url'] = engine.fetch_url
        self.initial['yaml_configuration'] = engine.yaml_configuration
        self.initial['vulnerability_scan'] = engine.vulnerability_scan


class AddWordlistForm(forms.Form):
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={'class': 'form-control',
                   'id': 'name',
                   'placeholder': 'my awesome wordlist', }))
    short_name = forms.CharField(
        required=True,
        validators=[validate_short_name],
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'short_name',
                'placeholder': 'my_awesome_wordlist', }))
    upload_file = forms.FileField(
        required=True,
        widget=forms.FileInput(
            attrs={'class': 'custom-file-input',
                   'id': 'txtFile',
                   'multiple': '',
                   'accept': '.txt', }))


class ConfigurationForm(forms.ModelForm):
    class Meta:
        model = Configuration
        fields = '__all__'
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(
            attrs={'class': 'form-control',
                   'id': 'name',
                   'placeholder': 'Configuration Name', }))
    short_name = forms.CharField(
        required=True,
        validators=[validate_short_name],
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'id': 'short_name',
                'placeholder': 'my_awesome_configuration', }))
    content = forms.CharField(widget=AceWidget(
            mode="text",
            theme="monokai",
            width="100%",
            height="450px",
            tabsize=4,
            fontsize=13,
            toolbar=True,))

    def set_value(self, configuration):
        self.initial['name'] = configuration.name
        self.initial['short_name'] = configuration.short_name
        self.initial['content'] = configuration.content
