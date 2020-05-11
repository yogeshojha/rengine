from django.db import models
from multiselectfield import MultiSelectField

SCAN_TYPES = (('subdomain_discovery', 'Subdomain Discovery'),
              ('visual_identification', 'Visual Idenfitication'),
              ('dir_file_search', 'Directory & Files Discovery'),
              ('subdomain_takeover', 'Subdomain Takeover'),
              ('param_discovery', 'Parameter Discovery'),
              ('port_scan', "Port Scan"))

class EngineType(models.Model):
    scan_type_name = models.CharField(max_length=200)
    my_field = MultiSelectField(choices=SCAN_TYPES)

    def __str__(self):
        return self.scan_type_name
