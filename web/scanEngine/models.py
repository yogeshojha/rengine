import yaml
from django.db import models


class hybrid_property:
    def __init__(self, func):
        self.func = func
        self.name = func.__name__
        self.exp = None

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return self.func(instance)

    def __set__(self, instance, value):
        pass

    def expression(self, exp):
        self.exp = exp
        return self

class EngineType(models.Model):
    id = models.AutoField(primary_key=True)
    engine_name = models.CharField(max_length=200)
    yaml_configuration = models.TextField()
    default_engine = models.BooleanField(null=True, default=False)

    def __str__(self):
        return self.engine_name

    def get_number_of_steps(self):
        return len(self.tasks) if self.tasks else 0

    @hybrid_property
    def tasks(self):
        if not self.yaml_configuration or not yaml.safe_load(self.yaml_configuration):
            return []
        return list(yaml.safe_load(self.yaml_configuration).keys())

class Wordlist(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, unique=True)
    count = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Configuration(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, unique=True)
    content = models.TextField()

    def __str__(self):
        return self.name


class InterestingLookupModel(models.Model):
    id = models.AutoField(primary_key=True)
    keywords = models.TextField(null=True, blank=True)
    custom_type = models.BooleanField(default=False)
    title_lookup = models.BooleanField(default=True)
    url_lookup = models.BooleanField(default=True)
    condition_200_http_lookup = models.BooleanField(default=False)


class Notification(models.Model):
    id = models.AutoField(primary_key=True)
    send_to_slack = models.BooleanField(default=False)
    send_to_lark = models.BooleanField(default=False)
    send_to_discord = models.BooleanField(default=False)
    send_to_telegram = models.BooleanField(default=False)

    slack_hook_url = models.CharField(max_length=200, null=True, blank=True)
    lark_hook_url = models.CharField(max_length=200, null=True, blank=True)
    discord_hook_url = models.CharField(max_length=200, null=True, blank=True)
    telegram_bot_token = models.CharField(max_length=100, null=True, blank=True)
    telegram_bot_chat_id = models.CharField(max_length=100, null=True, blank=True)

    send_scan_status_notif = models.BooleanField(default=True)
    send_interesting_notif = models.BooleanField(default=True)
    send_vuln_notif = models.BooleanField(default=True)
    send_subdomain_changes_notif = models.BooleanField(default=True)

    send_scan_output_file = models.BooleanField(default=True)
    send_scan_tracebacks = models.BooleanField(default=True)


class Proxy(models.Model):
    id = models.AutoField(primary_key=True)
    use_proxy = models.BooleanField(default=False)
    proxies = models.TextField(blank=True, null=True)


class Hackerone(models.Model):
    id = models.AutoField(primary_key=True)
    # TODO: username and api_key fields will be deprecated in another major release, Instead HackerOneAPIKey model from dasbhboard/models.py will be used
    username = models.CharField(max_length=100, null=True, blank=True) # unused
    api_key = models.CharField(max_length=200, null=True, blank=True) # unused
    send_report = models.BooleanField(default=False, null=True, blank=True)
    send_critical = models.BooleanField(default=True)
    send_high = models.BooleanField(default=True)
    send_medium = models.BooleanField(default=False)
    report_template = models.TextField(blank=True, null=True)


class VulnerabilityReportSetting(models.Model):
    id = models.AutoField(primary_key=True)
    primary_color = models.CharField(max_length=10, null=True, blank=True, default='#FFB74D')
    secondary_color = models.CharField(max_length=10, null=True, blank=True, default='#212121')
    company_name = models.CharField(max_length=100, null=True, blank=True)
    company_address = models.CharField(max_length=200, null=True, blank=True)
    company_email = models.CharField(max_length=100, null=True, blank=True)
    company_website = models.CharField(max_length=100, null=True, blank=True)
    show_rengine_banner = models.BooleanField(default=True)
    show_executive_summary = models.BooleanField(default=True)
    executive_summary_description = models.TextField(blank=True, null=True)
    show_footer = models.BooleanField(default=False)
    footer_text = models.CharField(max_length=200, null=True, blank=True)


class InstalledExternalTool(models.Model):
    id = models.AutoField(primary_key=True)
    logo_url = models.CharField(max_length=200, null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=2000)
    github_url = models.CharField(max_length=500)
    license_url = models.CharField(max_length=500, null=True, blank=True)
    version_lookup_command = models.CharField(max_length=200, null=True, blank=True)
    update_command = models.CharField(max_length=200, null=True, blank=True)
    install_command = models.CharField(max_length=200)
    version_match_regex = models.CharField(max_length=100, default='[vV]*(\d+\.)?(\d+\.)?(\*|\d+)', null=True, blank=True)
    is_default = models.BooleanField(default=False)
    is_subdomain_gathering = models.BooleanField(default=False)
    is_github_cloned = models.BooleanField(default=False)
    github_clone_path = models.CharField(max_length=1500, null=True, blank=True)
    subdomain_gathering_command = models.CharField(max_length=300, null=True, blank=True)

    def __str__(self):
        return self.name