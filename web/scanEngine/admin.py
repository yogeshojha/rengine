from django.contrib import admin
from scanEngine.models import EngineType, Wordlist, Configuration, InterestingLookupModel

# Register your models here.
admin.site.register(EngineType)
admin.site.register(Wordlist)
admin.site.register(Configuration)
admin.site.register(InterestingLookupModel)
