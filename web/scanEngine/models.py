from django.db import models
from django.contrib.admin.utils import flatten

class EngineType(models.Model):
    id = models.AutoField(primary_key=True)
    engine_name = models.CharField(max_length=200)
    subdomain_discovery = models.BooleanField()
    dir_file_search = models.BooleanField()
    port_scan = models.BooleanField()
    fetch_url = models.BooleanField()
    vulnerability_scan = models.BooleanField(null=True, default=False)
    osint = models.BooleanField(null=True, default=False)
    screenshot = models.BooleanField(null=True, default=True)
    yaml_configuration = models.TextField()
    default_engine = models.BooleanField(null=True, default=False)

    def __str__(self):
        return self.engine_name

    def get_number_of_steps(self):
        engine_list = [
            self.subdomain_discovery,
            self.dir_file_search,
            self.port_scan,
            self.fetch_url,
            self.vulnerability_scan,
            self.osint,
            self.screenshot
            ]
        return sum(bool(item) for item in engine_list)


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

    @classmethod
    def get_interesting_keywords(cls)->list:
        return cls.lookup_keywords
    
    @classmethod
    def set_interesting_keywords(cls) -> None:
        keywords_list = cls.objects.values_list(
        'keywords', flat=True)

        # split and flatten
        lookup_keywords = flatten([key.split(',') for key in keywords_list])
        # remove empty strings from list, if any
        cls.lookup_keywords = list(filter(None, lookup_keywords))


class Notification(models.Model):
    id = models.AutoField(primary_key=True)
    send_to_slack = models.BooleanField(default=False)
    send_to_discord = models.BooleanField(default=False)
    send_to_telegram = models.BooleanField(default=False)

    slack_hook_url = models.CharField(max_length=200, null=True, blank=True)
    discord_hook_url = models.CharField(max_length=200, null=True, blank=True)
    telegram_bot_token = models.CharField(max_length=100, null=True, blank=True)
    telegram_bot_chat_id = models.CharField(max_length=100, null=True, blank=True)

    send_scan_status_notif = models.BooleanField(default=True)
    send_interesting_notif = models.BooleanField(default=True)
    send_vuln_notif = models.BooleanField(default=True)
    send_subdomain_changes_notif = models.BooleanField(default=True)

    send_scan_output_file = models.BooleanField(default=True)


class Proxy(models.Model):
    id = models.AutoField(primary_key=True)
    use_proxy = models.BooleanField(default=False)
    proxies = models.TextField(blank=True, null=True)
