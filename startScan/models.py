import datetime

from django.db import models
from targetApp.models import Domain
from scanEngine.models import EngineType
from django.db.models import JSONField
from django.utils import timezone

class ScanHistory(models.Model):
    start_scan_date = models.DateTimeField()
    scan_status = models.IntegerField()
    domain_name = models.ForeignKey(Domain, on_delete=models.CASCADE)
    scan_type = models.ForeignKey(EngineType, on_delete=models.CASCADE)
    celery_id = models.CharField(max_length=100, blank=True)
    whois_json = JSONField(null=True)
    stop_scan_date = models.DateTimeField(null=True)

    def __str__(self):
        # debug purpose remove scan type and id in prod
        return self.domain_name.domain_name

    def get_subdomain_count(self):
        return Subdomain.objects.filter(scan_history__id=self.id).count()

    def get_endpoint_count(self):
        return EndPoint.objects.filter(scan_history__id=self.id).count()

    def get_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).count()

    def get_info_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).filter(
            severity=0).count()

    def get_low_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).filter(
            severity=1).count()

    def get_medium_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).filter(
            severity=2).count()

    def get_high_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).filter(
            severity=3).count()

    def get_critical_vulnerability_count(self):
        return Vulnerability.objects.filter(
            scan_history__id=self.id).filter(
            severity=4).count()

    def get_completed_time(self):
        return self.stop_scan_date - self.start_scan_date

    def get_completed_time_in_sec(self):
        return (self.stop_scan_date - self.start_scan_date).seconds

    def get_elapsed_time(self):
        duration = timezone.now() - self.start_scan_date
        days, seconds = duration.days, duration.seconds
        hours = days * 24 + seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        if not hours and not minutes:
            return '{} seconds'.format(seconds)
        elif not hours:
            return '{} minutes'.format(minutes)
        elif not minutes:
            return '{} hours'.format(hours)
        return '{} hours {} minutes'.format(hours, minutes)


class Subdomain(models.Model):
    scan_history = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    target_domain = models.ForeignKey(Domain, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=1000)
    cname = models.CharField(max_length=500, blank=True)
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
    checked = models.BooleanField(null=True, blank=True, default=False)
    discovered_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.name)


class EndPoint(models.Model):
    scan_history = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    target_domain = models.ForeignKey(Domain, on_delete=models.CASCADE, null=True, blank=True)
    subdomain = models.ForeignKey(Subdomain, on_delete=models.CASCADE, null=True, blank=True)
    http_url = models.CharField(max_length=5000)
    content_length = models.IntegerField(default=0)
    page_title = models.CharField(max_length=1000)
    http_status = models.IntegerField(default=0)
    content_type = models.CharField(max_length=100, null=True)
    discovered_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.page_title


class Vulnerability(models.Model):
    scan_history = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    endpoint = models.ForeignKey(EndPoint, on_delete=models.CASCADE, blank=True, null=True)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, null=True, blank=True)
    discovered_date = models.DateTimeField(null=True)
    http_url = models.CharField(max_length=8000, null=True)
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


class ScanActivity(models.Model):
    scan_of = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    title = models.CharField(max_length=1000)
    time = models.DateTimeField()
    status = models.IntegerField()

    def __str__(self):
        return str(self.title)
