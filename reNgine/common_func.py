
from django.db.models import Q
from functools import reduce
from scanEngine.models import InterestingLookupModel
from startScan.models import ScannedHost, WayBackEndPoint


def get_lookup_keywords():
    default_lookup_keywords = [
        key.strip() for key in InterestingLookupModel.objects.get(
            id=1).keywords.split(',')]
    custom_lookup_keywords = []
    if InterestingLookupModel.objects.filter(custom_type=True):
        custom_lookup_keywords = [
            key.strip() for key in InterestingLookupModel.objects.filter(
                custom_type=True).order_by('-id')[0].keywords.split(',')]
    lookup_keywords = default_lookup_keywords + custom_lookup_keywords
    # remove empty strings from list, if any
    lookup_keywords = list(filter(None, lookup_keywords))

    return lookup_keywords


def get_interesting_subdomains(scan_history=None, target=None):
    lookup_keywords = get_lookup_keywords()

    subdomain_lookup_query = Q()
    page_title_lookup_query = Q()

    for key in lookup_keywords:
        subdomain_lookup_query |= Q(subdomain__icontains=key)
        page_title_lookup_query |= Q(page_title__iregex="\\y{}\\y".format(key))

    if target:
        subdomain_lookup = ScannedHost.objects.filter(
            target_domain__id=target).filter(subdomain_lookup_query)
        title_lookup = ScannedHost.objects.filter(
            page_title_lookup_query).filter(target_domain__id=target)
    elif scan_history:
        subdomain_lookup = ScannedHost.objects.filter(
            scan_history__id=scan_history).filter(subdomain_lookup_query)
        title_lookup = ScannedHost.objects.filter(
            scan_history__id=scan_history).filter(page_title_lookup_query)

    return subdomain_lookup | title_lookup


def get_interesting_endpoint(scan_history=None, target=None):
    lookup_keywords = get_lookup_keywords()

    url_lookup_query = Q()
    page_title_lookup_query = Q()

    for key in lookup_keywords:
        url_lookup_query |= Q(http_url__icontains=key)
        page_title_lookup_query |= Q(page_title__iregex="\\y{}\\y".format(key))

    print(url_lookup_query)
    print(page_title_lookup_query)

    if target:
        url_lookup = WayBackEndPoint.objects.filter(
            target_domain__id=target).filter(url_lookup_query)
        title_lookup = WayBackEndPoint.objects.filter(
            target_domain__id=target).filter(page_title_lookup_query)
    elif scan_history:
        url_lookup = WayBackEndPoint.objects.filter(
            url_of__id=scan_history).filter(url_lookup_query)
        title_lookup = WayBackEndPoint.objects.filter(
            url_of__id=scan_history).filter(page_title_lookup_query)

    return url_lookup | title_lookup
