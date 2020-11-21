from django.db import models
from targetApp.models import Domain
from scanEngine.models import EngineType
from django.contrib.postgres.fields import JSONField


class ScanHistory(models.Model):
    last_scan_date = models.DateTimeField()
    scan_status = models.IntegerField()
    domain_name = models.ForeignKey(Domain, on_delete=models.CASCADE)
    scan_type = models.ForeignKey(EngineType, on_delete=models.CASCADE)
    celery_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        # debug purpose remove scan type and id in prod
        return self.domain_name.domain_name


class ScannedHost(models.Model):
    subdomain = models.CharField(max_length=1000)
    cname = models.CharField(max_length=500, blank=True)
    scan_history = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    open_ports = models.CharField(max_length=1000)
    http_status = models.IntegerField(default=0)
    content_length = models.IntegerField(default=0)
    page_title = models.CharField(max_length=1000)
    http_url = models.CharField(max_length=1000)
    ip_address = models.CharField(max_length=1000)
    is_ip_cdn = models.BooleanField(null=True, default=False)
    screenshot_path = models.CharField(max_length=1000, null=True)
    http_header_path = models.CharField(max_length=1000, null=True)
    technology_stack = models.CharField(max_length=1500, null=True)
    directory_json = JSONField(null=True)

    def __str__(self):
        return str(self.subdomain)


class WayBackEndPoint(models.Model):
    url_of = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    http_url = models.CharField(max_length=5000)
    content_length = models.IntegerField(default=0)
    page_title = models.CharField(max_length=1000)
    http_status = models.IntegerField(default=0)
    content_type = models.CharField(max_length=100, null=True)

    def __str__(self):
        return self.page_title


class ScanActivity(models.Model):
    scan_of = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    title = models.CharField(max_length=1000)
    time = models.DateTimeField()
    status = models.IntegerField()

    def __str__(self):
        return str(self.title)


class VulnerabilityScan(models.Model):
    vulnerability_of = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    host = models.ForeignKey(ScannedHost, on_delete=models.CASCADE, blank=True, null=True)
    discovered_date = models.DateTimeField(null=True)
    url = models.CharField(max_length=1000)
    name = models.CharField(max_length=400)
    severity = models.IntegerField()
    description = models.CharField(max_length=1000, null=True, blank=True)
    extracted_results = models.CharField(max_length=1000, null=True, blank=True)
    template_used = models.CharField(max_length=100)
    matcher_name = models.CharField(max_length=400, null=True, blank=True)
    open_status = models.BooleanField(null=True, blank=True, default=True)

    def __str__(self):
        return self.name

    def get_severity(self):
        return self.severity
