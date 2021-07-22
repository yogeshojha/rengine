from django.apps import AppConfig
from scanEngine.models import InterestingLookupModel


class ScanengineConfig(AppConfig):
    name = 'scanEngine'

    # hook to run this code once the process starts
    def ready(self):
        InterestingLookupModel.set_interesting_keywords()
