from django.contrib import admin
from scanEngine.models import EngineType, Wordlist, Configuration

# Register your models here.
admin.site.register(EngineType)
admin.site.register(Wordlist)
admin.site.register(Configuration)
