from django.core.management.base import BaseCommand
from reNgine.common_func import dump_custom_scan_engines
from reNgine.settings import RENGINE_CUSTOM_ENGINES


class Command(BaseCommand):
    help = 'Dumps custom engines into YAMLs in custom_engines/ folder'

    def handle(self, *args, **kwargs):
        return dump_custom_scan_engines(RENGINE_CUSTOM_ENGINES)