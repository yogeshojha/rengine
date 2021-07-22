from django.dispatch import receiver
from django.core.signals import post_save
from scanEngine.models import InterestingLookupModel


@receiver(post_save, sender=InterestingLookupModel)
def keywords_post_save_receiver(sender, **kwargs) -> None:
    sender.set_interesting_keywords()
