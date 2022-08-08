import json
import logging
import os
import random
import re
import shutil
import subprocess
from datetime import date
from functools import reduce
from threading import Thread
from urllib.parse import urlparse

import asyncwhois
import requests
import tldextract
from discord_webhook import DiscordWebhook
from django.db.models import Q
from lxml import html
from reNgine.common_serializers import *
from reNgine.definitions import *
from scanEngine.models import *
from startScan.models import *
from targetApp.models import *


def execute_live(cmd):
    """Execute a command while fetching it's output live."""
    popen = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        item = stdout_line.strip()
        if item.startswith(('{', '[')) and item.endswith(('}', ']')):
            try:
                yield json.loads(item)
                continue
            except Exception as e:
                pass
        yield item
    popen.stdout.close()
    return_code = popen.wait()
    return return_code

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
    extract_url = tldextract.extract(url)
    subdomain = '.'.join(extract_url[:4])
    if subdomain[0] == '.':
        subdomain = subdomain[1:]
    return subdomain.strip()

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

def get_random_proxy():
    if Proxy.objects.all().exists():
        proxy = Proxy.objects.all()[0]
        if proxy.use_proxy:
            proxy_name = random.choice(proxy.proxies.splitlines())
            print('Using proxy: ' + proxy_name)
            return proxy_name
    return False

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

def get_whois(ip_domain, save_db=False, fetch_from_db=True):
    domain_query = Domain.objects.filter(name=ip_domain)
    if fetch_from_db:
        if not domain_query.exists():
            return {
                'status': False,
                'message': f'Domain {ip_domain} does not exist as a Domain in the Database.'
            }
        domain_info = domain_query.first().domain_info
        return {
            'status': True,
            'ip_domain': ip_domain,
            'domain': {
                'created': domain_info.created,
                'updated': domain_info.updated,
                'expires': domain_info.expires,
                'registrar': DomainRegistrarSerializer(domain_info.registrar).data['name'],
                'geolocation_iso': DomainCountrySerializer(domain_info.registrant_country).data['name'],
                'dnssec': domain_info.dnssec,
                'status': [status['status'] for status in DomainWhoisStatusSerializer(domain_info.status, many=True).data]
            },
            'registrant': {
                'name': DomainRegisterNameSerializer(domain_info.registrant_name).data['name'],
                'organization': DomainRegisterOrganizationSerializer(domain_info.registrant_organization).data['name'],
                'address': DomainAddressSerializer(domain_info.registrant_address).data['name'],
                'city': DomainCitySerializer(domain_info.registrant_city).data['name'],
                'state': DomainStateSerializer(domain_info.registrant_state).data['name'],
                'zipcode': DomainZipCodeSerializer(domain_info.registrant_zip_code).data['name'],
                'country': DomainCountrySerializer(domain_info.registrant_country).data['name'],
                'phone': DomainPhoneSerializer(domain_info.registrant_phone).data['name'],
                'fax': DomainFaxSerializer(domain_info.registrant_fax).data['name'],
                'email': DomainEmailSerializer(domain_info.registrant_email).data['name'],
            },
            'admin': {
                'name': DomainRegisterNameSerializer(domain_info.admin_name).data['name'],
                'id': DomainRegistrarIDSerializer(domain_info.admin_id).data['name'],
                'organization': DomainRegisterOrganizationSerializer(domain_info.admin_organization).data['name'],
                'address': DomainAddressSerializer(domain_info.admin_address).data['name'],
                'city': DomainCitySerializer(domain_info.admin_city).data['name'],
                'state': DomainStateSerializer(domain_info.admin_state).data['name'],
                'zipcode': DomainZipCodeSerializer(domain_info.admin_zip_code).data['name'],
                'country': DomainCountrySerializer(domain_info.admin_country).data['name'],
                'phone': DomainPhoneSerializer(domain_info.admin_phone).data['name'],
                'fax': DomainFaxSerializer(domain_info.admin_fax).data['name'],
                'email': DomainEmailSerializer(domain_info.admin_email).data['name'],
            },
            'technical_contact': {
                'name': DomainRegisterNameSerializer(domain_info.tech_name).data['name'],
                'id': DomainRegistrarIDSerializer(domain_info.tech_id).data['name'],
                'organization': DomainRegisterOrganizationSerializer(domain_info.tech_organization).data['name'],
                'address': DomainAddressSerializer(domain_info.tech_address).data['name'],
                'city': DomainCitySerializer(domain_info.tech_city).data['name'],
                'state': DomainStateSerializer(domain_info.tech_state).data['name'],
                'zipcode': DomainZipCodeSerializer(domain_info.tech_zip_code).data['name'],
                'country': DomainCountrySerializer(domain_info.tech_country).data['name'],
                'phone': DomainPhoneSerializer(domain_info.tech_phone).data['name'],
                'fax': DomainFaxSerializer(domain_info.tech_fax).data['name'],
                'email': DomainEmailSerializer(domain_info.tech_email).data['name'],
            },
            'nameservers': [ns['name'] for ns in NameServersSerializer(domain_info.name_servers, many=True).data],
            'raw_text': domain_info.raw_text
        }

    # Fetch from whois
    result = asyncwhois.whois_domain(ip_domain)
    whois = result.parser_output
    if not whois.get('domain_name'):
        return {
            'status': False,
            'ip_domain': ip_domain,
            'result': 'Unable to fetch records from WHOIS database.'
        }
    created = whois.get('created')
    expires = whois.get('expires')
    updated = whois.get('updated')
    dnssec = whois.get('dnssec')

    # Save whois information in various tables
    if save_db and domain_query.exists():
        domain = domain_query.first()
        logger.info(f'Saving domain "{domain}" info in DB!')
        domain_info = DomainInfo(
            raw_text=result.query_output.strip(),
            dnsec=dnssec,
            created=created,
            updated=updated,
            expires=expires)

        # Record whois subfields in various DB models
        whois_fields = {
            ('default'): [
                ('registrar', DomainRegistrar),
                ('name_servers', NameServers)
            ],
            ('registrant'):
                [
                    ('name', DomainRegisterName),
                    ('organization', DomainRegisterOrganization),
                    ('address', DomainAddress),
                    ('city', DomainCity),
                    ('state', DomainState),
                    ('zipcode', DomainZipCode),
                    ('country', DomainCountry),
                    ('phone', DomainPhone),
                    ('fax', DomainFax),
                    ('email', DomainEmail)
                ],
            ('admin', 'tech'): [
                ('name', DomainRegisterName),
                ('id', DomainRegistrarID),
                ('organization', DomainRegisterOrganization),
                ('address', DomainAddress),
                ('city', DomainCity),
                ('state', DomainState),
                ('zipcode', DomainZipCode),
                ('country', DomainCountry),
                ('email', DomainEmail),
                ('phone', DomainPhone),
                ('fax', DomainFax)
            ]
        }
        objects = {}
        logger.info(f'Gathering domain details for {ip_domain}...')
        for field_parents, fields in whois_fields.items():
            for field_parent in field_parents:
                for (field_name, model_cls) in fields:
                    field_fullname = f'{field_parent}_{field_name}' if field_parent != 'default' else field_name
                    field_content = whois.get(field_fullname)
                    serializer_cls = globals()[model_cls.__name__ + 'Serializer']

                    # If field is an email, parse it with a regex
                    if field_name == 'email':
                        email_search = EMAIL_REGEX.search(str(field_content))
                        field_content = email_search.group(0) if email_search else None

                    # Skip empty fields
                    if not field_content:
                        continue

                    # Create object in database
                    obj, created = model_cls.objects.get_or_create(name=field_content)
                    obj_json = serializer_cls(obj, many=False).data
                    objects[field_fullname] = obj_json
                    if created:
                        logger.info(f'Saved {obj} in DB !')

                    # Set attribute in domain_info
                    setattr(domain_info, field_fullname, obj)
                    domain_info.save()

        logger.info(f'Finished saving domain info {ip_domain}.')

        # Whois status
        whois_status = whois.get('status', [])
        for _status in whois_status:
            domain_whois, _ = DomainWhoisStatus.objects.get_or_create(status=_status)
            domain_info.status.add(domain_whois)
            domain_whois_json = DomainWhoisStatusSerializer(domain_whois, many=False).data
            if 'whois_status' in objects:
                objects['whois_status'].append(domain_whois_json)
            else:
                objects['whois_status'] = [domain_whois_json]

        # Nameservers
        nameservers = whois.get('name_servers', [])
        for name_server in nameservers:
            ns, _ = NameServers.objects.get_or_create(name=name_server)
            domain_info.name_servers.add(ns)
            ns_json = NameServersSerializer(ns, many=False).data
            if 'name_servers' in objects:
                objects['name_servers'].append(ns_json)
            else:
                objects['name_servers'] = [ns_json]

        # Save domain in DB
        domain.domain_info = domain_info
        domain.save()

        return {
            'status': True,
            'ip_domain': ip_domain,
            'domain': {
                'created': created,
                'updated': updated,
                'expires': expires,
                'registrar': domain_info.registrar,
                'geolocation_iso': objects[('registrant')]['country'],
                'dnssec': dnssec,
                'status': _status,
            },
            'registrant': objects[('registrant')],
            'admin': objects['admin'],
            'technical_contact': objects['tech'],
            'nameservers': objects['name_servers'],
            'raw_text': result.query_output.strip()
        }


def get_cms_details(url):
    # this function will fetch cms details using cms_detector
    response = {}
    cms_detector_command = 'python3 /usr/src/github/CMSeeK/cmseek.py --random-agent --batch --follow-redirect'
    subprocess_splitted_command = cms_detector_command.split()
    subprocess_splitted_command.append('-u')
    subprocess_splitted_command.append(url)
    process = subprocess.Popen(subprocess_splitted_command)
    process.wait()

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


def remove_cmd_injection_chars(command):
    remove_chars = ['&', '<', '>', '|', ';', '$', '`']
    for chrs in remove_chars:
        command = command.replace(chrs, '')
    return command
