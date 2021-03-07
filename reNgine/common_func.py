from scanEngine.models import InterestingLookupModel
from startScan.models import ScannedHost


def get_interesting_subdomains(scan_history=None, target=None):
    default_lookup_keywords = InterestingLookupModel.objects.get(
        id=1).keywords.split(',')
    custom_lookup_keywords = []
    if InterestingLookupModel.objects.filter(custom_type=True):
        custom_lookup_keywords = InterestingLookupModel.objects.filter(
            custom_type=True).order_by('-id')[0].keywords.split(',')
    lookup_keywords = default_lookup_keywords + custom_lookup_keywords
    subdomain_lookup = ScannedHost.objects.none()
    page_title_lookup = ScannedHost.objects.none()
    for key in lookup_keywords:
        if scan_history:
            subdomain_lookup = subdomain_lookup | ScannedHost.objects.filter(
                scan_history__id=scan_history).filter(subdomain__icontains=key)
            page_title_lookup = page_title_lookup | ScannedHost.objects.filter(
                scan_history__id=scan_history).filter(
                page_title__iregex="\\y{}\\y".format(key))
        elif target:
            subdomain_lookup = subdomain_lookup | ScannedHost.objects.filter(
                target_domain__id=target).filter(subdomain__icontains=key)
            page_title_lookup = page_title_lookup | ScannedHost.objects.filter(
                target_domain__id=target).filter(page_title__iregex="\\y{}\\y".format(key))
    print(subdomain_lookup)
    return subdomain_lookup | page_title_lookup
