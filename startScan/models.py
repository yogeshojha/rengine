from django.db import models

class SubdomainModel(models.Model):
    hello = models.CharField(max_length=500)
