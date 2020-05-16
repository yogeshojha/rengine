from django.db import models
from targetApp.models import Domain
from scanEngine.models import EngineType

class ScanHistory(models.Model):
    last_scan_date = models.DateTimeField()
    scan_status = models.IntegerField()
    domain_name = models.ForeignKey(Domain, on_delete=models.CASCADE)
    scan_type = models.ForeignKey(EngineType, on_delete=models.CASCADE)

    def __str__(self):
        # debug purpose remove scan type and id in prod
        return self.domain_name.domain_name + self.scan_type.scan_type_name + str(self.id)

class ScannedSubdomains(models.Model):
    subdomain = models.CharField(max_length=100)
    scan_history = models.ForeignKey(ScanHistory, on_delete=models.CASCADE)
    open_ports = models.CharField(max_length=1000)
    takeover_possible = models.BooleanField()
    http_status = models.IntegerField()
    alive_subdomain = models.BooleanField()
    technology_stack = models.CharField(max_length=1000)

    def __str__(self):
        return self.subdomain
