from django.db import models
from targetApp.models import Domain
from scanEngine.models import EngineType

class SubdomainModel(models.Model):
    last_scan_date = models.DateTimeField()
    domain_name = models.ForeignKey(Domain, on_delete=models.CASCADE)
    scan_type = models.ForeignKey(EngineType, on_delete=models.CASCADE)

    def __str__(self):
        return self.domain_name.domain_name
