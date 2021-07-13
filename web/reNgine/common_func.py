import os
import json
import tldextract
import requests
from threading import Thread

from discord_webhook import DiscordWebhook
from django.db.models import Q
from functools import reduce
from scanEngine.models import *
from startScan.models import Subdomain, EndPoint


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
        if InterestingLookupModel.objects.filter(custom_type=True).exists():
            if InterestingLookupModel.objects.filter(
                    custom_type=True).order_by('-id')[0].url_lookup:
                subdomain_lookup_query |= Q(name__icontains=key)
            if InterestingLookupModel.objects.filter(
                    custom_type=True).order_by('-id')[0].title_lookup:
                page_title_lookup_query |= Q(
                    page_title__iregex="\\y{}\\y".format(key))
        else:
            subdomain_lookup_query |= Q(name__icontains=key)
            page_title_lookup_query |= Q(
                page_title__iregex="\\y{}\\y".format(key))

    if InterestingLookupModel.objects.filter(
            custom_type=True) and InterestingLookupModel.objects.filter(
            custom_type=True).order_by('-id')[0].condition_200_http_lookup:
        subdomain_lookup_query &= Q(http_status__exact=200)
        page_title_lookup_query &= Q(http_status__exact=200)

    subdomain_lookup = Subdomain.objects.none()
    title_lookup = Subdomain.objects.none()

    if target:
        if subdomain_lookup_query:
            subdomain_lookup = Subdomain.objects.filter(
                target_domain__id=target).filter(subdomain_lookup_query).distinct('name')
        if page_title_lookup_query:
            title_lookup = Subdomain.objects.filter(page_title_lookup_query).filter(
                target_domain__id=target).distinct('name')
    elif scan_history:
        if subdomain_lookup_query:
            subdomain_lookup = Subdomain.objects.filter(
                scan_history__id=scan_history).filter(subdomain_lookup_query)
        if page_title_lookup_query:
            title_lookup = Subdomain.objects.filter(
                scan_history__id=scan_history).filter(page_title_lookup_query)
    else:
        if subdomain_lookup_query:
            subdomain_lookup = Subdomain.objects.filter(subdomain_lookup_query)
        if page_title_lookup_query:
            title_lookup = Subdomain.objects.filter(page_title_lookup_query)
    return subdomain_lookup | title_lookup


def get_interesting_endpoint(scan_history=None, target=None):
    lookup_keywords = get_lookup_keywords()

    url_lookup_query = Q()
    page_title_lookup_query = Q()

    for key in lookup_keywords:
        if InterestingLookupModel.objects.filter(custom_type=True).exists():
            if InterestingLookupModel.objects.filter(custom_type=True).order_by('-id')[0].url_lookup:
                url_lookup_query |= Q(http_url__icontains=key)
            if InterestingLookupModel.objects.filter(custom_type=True).order_by('-id')[0].title_lookup:
                page_title_lookup_query |= Q(page_title__iregex="\\y{}\\y".format(key))

        else:
            url_lookup_query |= Q(http_url__icontains=key)
            page_title_lookup_query |= Q(page_title__iregex="\\y{}\\y".format(key))

    if InterestingLookupModel.objects.filter(custom_type=True) and InterestingLookupModel.objects.filter(custom_type=True).order_by('-id')[0].condition_200_http_lookup:
        url_lookup_query &= Q(http_status__exact=200)
        page_title_lookup_query &= Q(http_status__exact=200)

    url_lookup = EndPoint.objects.none()
    title_lookup = EndPoint.objects.none()

    if target:
        if url_lookup_query:
            url_lookup = EndPoint.objects.filter(
                target_domain__id=target).filter(url_lookup_query).distinct('http_url')
        if page_title_lookup_query:
            title_lookup = EndPoint.objects.filter(
                target_domain__id=target).filter(page_title_lookup_query).distinct('http_url')
    elif scan_history:
        if url_lookup_query:
            url_lookup = EndPoint.objects.filter(
                scan_history__id=scan_history).filter(url_lookup_query)
        if page_title_lookup_query:
            title_lookup = EndPoint.objects.filter(
                scan_history__id=scan_history).filter(page_title_lookup_query)

    else:
        if url_lookup_query:
            url_lookup = EndPoint.objects.filter(url_lookup_query)
        if page_title_lookup_query:
            title_lookup = EndPoint.objects.filter(page_title_lookup_query)

    return url_lookup | title_lookup

def check_keyword_exists(keyword_list, subdomain):
    return any(sub in subdomain for sub in keyword_list)

def get_subdomain_from_url(url):
    extract_url = tldextract.extract(url)
    subdomain = '.'.join(extract_url[:4])
    if subdomain[0] == '.':
        subdomain = subdomain[1:]
    return subdomain

def get_domain_from_subdomain(subdomain):
    ext = tldextract.extract(subdomain)
    return '.'.join(ext[1:3])

def send_telegram_message(message):
    notification = Notification.objects.all()
    if notification and notification[0].send_to_telegram \
    and notification[0].telegram_bot_token \
    and notification[0].telegram_bot_chat_id:
        telegram_bot_token = notification[0].telegram_bot_token
        telegram_bot_chat_id = notification[0].telegram_bot_chat_id
        send_text = 'https://api.telegram.org/bot' + telegram_bot_token \
            + '/sendMessage?chat_id=' + telegram_bot_chat_id \
            + '&parse_mode=Markdown&text=' + message
        thread = Thread(target=requests.get, args = (send_text, ))
        thread.start()

def send_slack_message(message):
    headers = {'content-type': 'application/json'}
    message = {'text': message}
    notification = Notification.objects.all()
    if notification and notification[0].send_to_slack \
    and notification[0].slack_hook_url:
        hook_url = notification[0].slack_hook_url
        thread = Thread(
            target=requests.post,
            kwargs = {
                'url': hook_url,
                'data': json.dumps(message),
                'headers': headers,
            })
        thread.start()

def send_discord_message(message):
    notification = Notification.objects.all()
    if notification and notification[0].send_to_discord \
    and notification[0].discord_hook_url:
        webhook = DiscordWebhook(
            url=notification[0].discord_hook_url,
            content=message,
            rate_limit_retry=True
            )
        thread = Thread(target=webhook.execute)
        thread.start()

def send_files_to_discord(file_path):
    notification = Notification.objects.all()
    if notification and notification[0].send_to_discord \
    and notification[0].discord_hook_url:
        webhook = DiscordWebhook(
            url=notification[0].discord_hook_url,
            rate_limit_retry=True,
            username="Scan Results - File"
        )
        with open(file_path, "rb") as f:
            head, tail = os.path.split(file_path)
            webhook.add_file(file=f.read(), filename=tail)
        thread = Thread(target=webhook.execute)
        thread.start()

def send_notification(message):
    send_slack_message(message)
    send_discord_message(message)
    send_telegram_message(message)
