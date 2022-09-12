import json
import logging
import os
import random
import shutil
from datetime import date
from threading import Thread
from urllib.parse import urlparse

import requests
import tldextract
from discord_webhook import DiscordWebhook
from django.db.models import Q
from reNgine.common_serializers import *
from reNgine.definitions import *
from scanEngine.models import *
from startScan.models import *
from targetApp.models import *

logger = logging.getLogger(__name__)


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
    lookup_keywords = list(filter(None, lookup_keywords)) # remove empty strings from list
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
        subdomains = Subdomain.objects.filter(target_domain__id=target)
        if subdomain_lookup_query:
            subdomain_lookup = subdomains.filter(subdomain_lookup_query)
        if page_title_lookup_query:
            title_lookup = subdomains.filter(page_title_lookup_query)
    elif scan_history:
        subdomains = Subdomain.objects.filter(scan_history__id=scan_history)
        if subdomain_lookup_query:
            subdomain_lookup = subdomains.filter(subdomain_lookup_query)
        if page_title_lookup_query:
            title_lookup = subdomains.filter(page_title_lookup_query)
    else:
        if subdomain_lookup_query:
            subdomain_lookup = Subdomain.objects.filter(subdomain_lookup_query)
        if page_title_lookup_query:
            title_lookup = Subdomain.objects.filter(page_title_lookup_query)
    lookup = subdomain_lookup | title_lookup
    return lookup


def get_interesting_endpoint(scan_history=None, target=None):
    lookup_keywords = get_lookup_keywords()

    url_lookup_query = Q()
    page_title_lookup_query = Q()

    for key in lookup_keywords:
        if InterestingLookupModel.objects.filter(custom_type=True).exists():
            if InterestingLookupModel.objects.filter(custom_type=True).order_by('-id')[0].url_lookup:
                url_lookup_query |= Q(http_url__icontains=key)
            if InterestingLookupModel.objects.filter(custom_type=True).order_by('-id')[0].title_lookup:
                page_title_lookup_query |= Q(page_title__iregex=f"\\y{key}\\y")

        else:
            url_lookup_query |= Q(http_url__icontains=key)
            page_title_lookup_query |= Q(page_title__iregex=f"\\y{key}\\y")

    if InterestingLookupModel.objects.filter(custom_type=True) and InterestingLookupModel.objects.filter(custom_type=True).order_by('-id')[0].condition_200_http_lookup:
        url_lookup_query &= Q(http_status__exact=200)
        page_title_lookup_query &= Q(http_status__exact=200)

    url_lookup = EndPoint.objects.none()
    title_lookup = EndPoint.objects.none()

    if target:
        urls = EndPoint.objects.filter(target_domain__id=target).distinct('http_url')
        if url_lookup_query:
            url_lookup = urls.filter(url_lookup_query)
        if page_title_lookup_query:
            title_lookup = urls.filter(page_title_lookup_query)
    elif scan_history:
        urls = EndPoint.objects.filter(scan_history__id=scan_history)
        if url_lookup_query:
            url_lookup = urls.filter(url_lookup_query)
        if page_title_lookup_query:
            title_lookup = urls.filter(page_title_lookup_query)

    else:
        if url_lookup_query:
            url_lookup = EndPoint.objects.filter(url_lookup_query)
        if page_title_lookup_query:
            title_lookup = EndPoint.objects.filter(page_title_lookup_query)

    return url_lookup | title_lookup


def check_keyword_exists(keyword_list, subdomain):
    return any(sub in subdomain for sub in keyword_list)

def get_subdomain_from_url(url):
    url_obj = urlparse(url.strip())
    url_str = url_obj.netloc if url_obj.scheme else url_obj.path
    return url_str.split(':')[0]


def get_domain_from_subdomain(subdomain):
    ext = tldextract.extract(subdomain)
    return '.'.join(ext[1:3])


def send_telegram_message(message):
    notification = Notification.objects.first()
    if notification and notification.send_to_telegram \
    and notification.telegram_bot_token \
    and notification.telegram_bot_chat_id:
        telegram_bot_token = notification.telegram_bot_token
        telegram_bot_chat_id = notification.telegram_bot_chat_id
        send_text = 'https://api.telegram.org/bot' + telegram_bot_token \
            + '/sendMessage?chat_id=' + telegram_bot_chat_id \
            + '&parse_mode=Markdown&text=' + message
        thread = Thread(target=requests.get, args = (send_text, ))
        thread.start()


def send_slack_message(message):
    headers = {'content-type': 'application/json'}
    message = {'text': message}
    notification = Notification.objects.first()
    if notification and notification.send_to_slack \
    and notification.slack_hook_url:
        hook_url = notification.slack_hook_url
        thread = Thread(
            target=requests.post,
            kwargs = {
                'url': hook_url,
                'data': json.dumps(message),
                'headers': headers,
            })
        thread.start()


def send_discord_message(message):
    notification = Notification.objects.first()
    if notification and notification.send_to_discord \
    and notification.discord_hook_url:
        webhook = DiscordWebhook(
            url=notification.discord_hook_url,
            content=message,
            rate_limit_retry=True
            )
        thread = Thread(target=webhook.execute)
        thread.start()


def send_file_to_discord(file_path, title=None):
    notification = Notification.objects.first()
    if notification and notification.send_to_discord \
    and notification.discord_hook_url:
        webhook = DiscordWebhook(
            url=notification.discord_hook_url,
            rate_limit_retry=True,
            username=title or "Scan Results - File"
        )
        with open(file_path, "rb") as f:
            head, tail = os.path.split(file_path)
            webhook.add_file(file=f.read(), filename=tail)
        thread = Thread(target=webhook.execute)
        thread.start()


def send_notification(message, scan_history_id=None):
    if scan_history_id is not None:
        message = f'`#{scan_history_id}`: {message}'
    send_slack_message(message)
    send_discord_message(message)
    send_telegram_message(message)


def get_random_proxy():
    """Get a random proxy from the list of proxies input by user in the UI."""
    if not Proxy.objects.all().exists():
        return False
    proxy = Proxy.objects.first()
    if not proxy.use_proxy:
        return False
    proxy_name = random.choice(proxy.proxies.splitlines())
    logger.warning('Using proxy: ' + proxy_name)
    # os.environ['HTTP_PROXY'] = proxy_name
    # os.environ['HTTPS_PROXY'] = proxy_name
    return proxy_name


def send_hackerone_report(vulnerability_id):
    vulnerability = Vulnerability.objects.get(id=vulnerability_id)
    severities = {v: k for k,v in NUCLEI_SEVERITY_MAP.items()}
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    # can only send vulnerability report if team_handle exists
    if len(vulnerability.target_domain.h1_team_handle) !=0:
        hackerone_query = Hackerone.objects.all()
        if hackerone_query.exists():
            hackerone = Hackerone.objects.first()
            severity_value = severities[vulnerability.severity]
            tpl = hackerone.report_template

            # Replace syntax of report template with actual content
            tpl = tpl.replace('{vulnerability_name}', vulnerability.name)
            tpl = tpl.replace('{vulnerable_url}', vulnerability.http_url)
            tpl = tpl.replace('{vulnerability_severity}', severity_value)
            tpl = tpl.replace('{vulnerability_description}', vulnerability.description if vulnerability.description else '')
            tpl = tpl.replace('{vulnerability_extracted_results}', vulnerability.extracted_results if vulnerability.extracted_results else '')
            tpl = tpl.replace('{vulnerability_reference}', vulnerability.reference if vulnerability.reference else '')

            data = {
              "data": {
                "type": "report",
                "attributes": {
                  "team_handle": vulnerability.target_domain.h1_team_handle,
                  "title": '{} found in {}'.format(vulnerability.name, vulnerability.http_url),
                  "vulnerability_information": tpl,
                  "severity_rating": severity_value,
                  "impact": "More information about the impact and vulnerability can be found here: \n" + vulnerability.reference if vulnerability.reference else "NA",
                }
              }
            }

            r = requests.post(
              'https://api.hackerone.com/v1/hackers/reports',
              auth=(hackerone.username, hackerone.api_key),
              json=data,
              headers=headers
            )
            response = r.json()
            status_code = r.status_code
            if status_code == 201:
                vulnerability.hackerone_report_id = response['data']["id"]
                vulnerability.open_status = False
                vulnerability.save()
            return status_code

    else:
        logger.error('No team handle found.')
        status_code = 111
        return status_code


def calculate_age(created):
    today = date.today()
    return today.year - created.year - ((today.month, today.day) < (created.month, created.day))


def return_zeorth_if_list(variable):
    return variable[0] if type(variable) == list else variable


def get_cms_details(url):
    # this function will fetch cms details using cms_detector
    response = {}
    cms_detector_command = f'python3 /usr/src/github/CMSeeK/cmseek.py --random-agent --batch --follow-redirect -u {url}'
    os.system(cms_detector_command)

    response['status'] = False
    response['message'] = 'Could not detect CMS!'

    parsed_url = urlparse(url)

    domain_name = parsed_url.hostname
    port = parsed_url.port

    find_dir = domain_name

    if port:
        find_dir += '_{}'.format(port)

    # subdomain may also have port number, and is stored in dir as _port

    cms_dir_path =  '/usr/src/github/CMSeeK/Result/{}'.format(find_dir)
    cms_json_path =  cms_dir_path + '/cms.json'

    if os.path.isfile(cms_json_path):
        cms_file_content = json.loads(open(cms_json_path, 'r').read())
        if not cms_file_content.get('cms_id'):
            return response
        response = {}
        response = cms_file_content
        response['status'] = True
        # remove cms dir path
        try:
            shutil.rmtree(cms_dir_path)
        except Exception as e:
            print(e)

    return response