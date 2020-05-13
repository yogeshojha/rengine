from django.db import models
from targetApp.models import Domain
from scanEngine.models import EngineType

class SubdomainModel(models.Model):
    
    def __str__(self):
        return self.domain_name
