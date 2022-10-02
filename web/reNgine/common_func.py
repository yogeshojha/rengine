import os
import re
import json
import random
import requests
import tldextract
import logging
import shutil
import subprocess
import asyncwhois

from threading import Thread
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from lxml import html
from datetime import datetime, date
from discord_webhook import DiscordWebhook
from functools import reduce
from rest_framework import serializers

from django.db.models import Q
from scanEngine.models import *
from startScan.models import *
from targetApp.models import *
from reNgine.definitions import *
from reNgine.common_serializers import *

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

def get_random_proxy():
    if Proxy.objects.all().exists():
        proxy = Proxy.objects.all()[0]
        if proxy.use_proxy:
            proxy_name = random.choice(proxy.proxies.splitlines())
            print('Using proxy: ' + proxy_name)
            return proxy_name
    return False

def send_hackerone_report(vulnerability_id):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    # get hackerone creds
    vulnerability = Vulnerability.objects.get(id=vulnerability_id)
    # can only send vulnerability report if team_handle exists
    if len(vulnerability.target_domain.h1_team_handle) !=0:
        if Hackerone.objects.all().exists():
            hackerone = Hackerone.objects.all()[0]
            if vulnerability.severity == 0:
                severity_value = 'none'
            elif vulnerability.severity == 1:
                severity_value = 'low'
            elif vulnerability.severity == 2:
                severity_value = 'medium'
            elif vulnerability.severity == 3:
                severity_value = 'high'
            elif vulnerability.severity == 4:
                severity_value = 'critical'
            report_template = hackerone.report_template
            # Replace syntax of report template with actual content
            if '{vulnerability_name}' in report_template:
                report_template = report_template.replace('{vulnerability_name}', vulnerability.name)
            if '{vulnerable_url}' in report_template:
                report_template = report_template.replace('{vulnerable_url}', vulnerability.http_url)
            if '{vulnerability_severity}' in report_template:
                report_template = report_template.replace('{vulnerability_severity}', severity_value)
            if '{vulnerability_description}' in report_template:
                report_template = report_template.replace('{vulnerability_description}', vulnerability.description if vulnerability.description else '')
            if '{vulnerability_extracted_results}' in report_template:
                report_template = report_template.replace('{vulnerability_extracted_results}', vulnerability.extracted_results if vulnerability.extracted_results else '')
            if '{vulnerability_reference}' in report_template:
                report_template = report_template.replace('{vulnerability_reference}', vulnerability.reference if vulnerability.reference else '')

            data = {
              "data": {
                "type": "report",
                "attributes": {
                  "team_handle": vulnerability.target_domain.h1_team_handle,
                  "title": '{} found in {}'.format(vulnerability.name, vulnerability.http_url),
                  "vulnerability_information": report_template,
                  "severity_rating": severity_value,
                  "impact": "More information about the impact and vulnerability can be found here: \n" + vulnerability.reference if vulnerability.reference else "NA",
                }
              }
            }

            r = requests.post(
              'https://api.hackerone.com/v1/hackers/reports',
              auth=(hackerone.username, hackerone.api_key),
              json = data,
              headers = headers
            )

            response = r.json()

            # print(response)

            status_code = r.status_code
            print(status_code)

            if status_code == 201:
                vulnerability.hackerone_report_id = response['data']["id"]
                vulnerability.open_status = False
                vulnerability.save()

            return status_code

    else:
        print('No target ')
        status_code = 111

        return status_code

def get_whois_using_domainbigdata(ip_domain, save_db=False, fetch_from_db=True):
    # CURRENTLY DEPRECATED!!!!!!
    # this function will fetch whois details for domains
    # if save_db = True, then the whois will be saved in db
    # if fetch_from_db = True then whois will be fetched from db, no lookup on
    #     bigdomain data will be done
    if ip_domain and not fetch_from_db:
        response = requests.get('https://domainbigdata.com/{}'.format(ip_domain))
        tree = html.fromstring(response.content)
        try:
            #RegistrantInfo Model
            name = tree.xpath('//*[@id="trRegistrantName"]/td[2]/a/text()')
            organization = tree.xpath('//*[@id="MainMaster_trRegistrantOrganization"]/td[2]/a/text()')
            email = tree.xpath('//*[@id="trRegistrantEmail"]/td[2]/a/text()')
            address = tree.xpath('//*[@id="trRegistrantAddress"]/td[2]/text()')
            city = tree.xpath('//*[@id="trRegistrantCity"]/td[2]/text()')
            state = tree.xpath('//*[@id="trRegistrantState"]/td[2]/text()')
            country = tree.xpath('//*[@id="trRegistrantCountry"]/td[2]/text()')
            country_iso = tree.xpath('//*[@id="imgFlagRegistrant"]/@alt')
            tel = tree.xpath('//*[@id="trRegistrantTel"]/td[2]/text()')
            fax = tree.xpath('//*[@id="trRegistrantFax"]/td[2]/text()')

            #finding domain association using organization
            organization_association_href = tree.xpath('//*[@id="MainMaster_trRegistrantOrganization"]/td[2]/a/@href')
            #finding domain association using email
            email_association_href = tree.xpath('//*[@id="trRegistrantEmail"]/td[2]/a/@href')

            # related tlds
            related_tlds = tree.xpath('//*[@id="divListOtherTLD"]/descendant::*/text()')

            # whois model
            whois = tree.xpath('//*[@id="whois"]/div/div[3]/text()')
            whois = "\n".join(whois).strip()

            # DomainInfo Model
            date_created = tree.xpath('//*[@id="trDateCreation"]/td[2]/text()')
            domain_age = tree.xpath('//*[@id="trWebAge"]/td[2]/text()')
            ip_address = tree.xpath('//*[@id="trIP"]/td[2]/a/text()')
            geolocation = tree.xpath('//*[@id="imgFlag"]/following-sibling::text()')
            geolocation_iso = tree.xpath('//*[@id="imgFlag"]/@alt')

            is_private_path = tree.xpath("//*[contains(@class, 'websiteglobalstats')]/tr[10]/td[2]/span/text()")
            is_private = False
            if len(is_private_path) > 0:
                is_private = True


            date_created = date_created[0].strip() if date_created else None
            domain_age = domain_age[0].strip() if domain_age else None
            ip_address = ip_address[0].strip() if ip_address else None
            geolocation = geolocation[0].strip() if geolocation else None
            geolocation_iso = geolocation_iso[0].strip() if geolocation_iso else None
            name = name[0].strip() if name else None
            organization = organization[0].strip() if organization else None
            email = email[0].strip() if email else None
            address = address[0].strip() if address else None
            city = city[0].strip() if city else None
            state = state[0].strip() if state else None
            country = country[0].strip() if country else None
            country_iso = country_iso[0].strip() if country_iso else None
            tel = tel[0].strip() if tel else None
            fax = fax[0].strip() if fax else None

            # association
            organization_association_href = organization_association_href[0].strip() if organization_association_href else None
            email_association_href = email_association_href[0].strip() if email_association_href else None

            # other tlds
            related_tlds = [ tld for tld in related_tlds if "\r\n" not in tld ]

            dns_history_xpath = tree.xpath("//*[@id='MainMaster_divNSHistory']/table/tbody/tr")
            dns_history = []
            for table_row in dns_history_xpath:
                row = table_row.xpath('td/text()')
                dns_history.append(
                    {
                        'date': row[0],
                        'action': row[1],
                        'nameserver': row[2],
                    }
                )

            associated_domains = []
            if organization_association_href and organization not in IGNORE_WHOIS_RELATED_KEYWORD:
                # get all associated domains using organization
                response_org = requests.get('https://domainbigdata.com{}'.format(organization_association_href))
                tree_org = html.fromstring(response_org.content)
                associated_domains_tree = tree_org.xpath('//*[@id="aDomain"]/text()')
                for domain in associated_domains_tree:
                    associated_domains.append(domain)

            if email_association_href and email not in IGNORE_WHOIS_RELATED_KEYWORD:
                print(email_association_href)
                response_email = requests.get('https://domainbigdata.com{}'.format(email_association_href))
                tree_email = html.fromstring(response_email.content)
                associated_domains_tree = tree_email.xpath('//*[@id="aDomain"]/text()')
                for domain in associated_domains_tree:
                    associated_domains.append(domain)

            # unique associated_domains
            unique_associated_domains = []
            [unique_associated_domains.append(domain) for domain in associated_domains if domain not in unique_associated_domains]

            # save in db
            if save_db and Domain.objects.filter(name=ip_domain).exists():
                # look for domain and save in db
                domain = Domain.objects.get(name=ip_domain)


                # check if registrant exists
                if RegistrantInfo.objects.filter(email=email).filter(name=name).exists():
                    registrant = RegistrantInfo.objects.get(email=email, name=name)
                else:
                    registrant = RegistrantInfo()
                    registrant.name = name
                    registrant.organization = organization
                    registrant.email = email
                    registrant.address = address
                    registrant.city = city
                    registrant.state = state
                    registrant.country = country
                    registrant.country_iso = country_iso
                    registrant.phone_number = tel
                    registrant.fax = fax
                    registrant.organization_association_href = organization_association_href
                    registrant.email_association_href = email_association_href
                    registrant.save()

                if WhoisDetail.objects.filter(details=whois).exists():
                    whois_model = WhoisDetail.objects.get(details=whois)
                else:
                    whois_model = WhoisDetail()
                    whois_model.details = whois if whois else None
                    whois_model.registrant = registrant
                    whois_model.save()

                domain_info = DomainInfo()
                domain_info.date_created = date_created
                domain_info.domain_age = domain_age
                domain_info.ip_address = ip_address
                domain_info.geolocation = geolocation
                domain_info.geolocation_iso = geolocation_iso
                domain_info.whois = whois_model
                domain_info.save()

                for table_row in dns_history_xpath:
                    row = table_row.xpath('td/text()')
                    ns_history = NameServerHistory()
                    ns_history.date = row[0]
                    ns_history.action = row[1]
                    ns_history.server = row[2]
                    ns_history.save()

                    domain_info.nameserver_history.add(ns_history);

                domain.domain_info = domain_info
                domain.save()


                # save associated domains
                for domain in unique_associated_domains:
                    if AssociatedDomain.objects.filter(name=domain).exists():
                        ass_domain = AssociatedDomain.objects.get(name=domain)
                    else:
                        ass_domain = AssociatedDomain()
                        ass_domain.name = domain
                        ass_domain.save()
                    domain_info.associated_domains.add(ass_domain)

                # save related TLDs
                for tld in related_tlds:
                    if RelatedTLD.objects.filter(name=tld).exists():
                        rel_tld = RelatedTLD.objects.get(name=tld)
                    else:
                        rel_tld = RelatedTLD()
                        rel_tld.name = tld
                        rel_tld.save()
                    domain_info.related_tlds.add(rel_tld)

            ns_records = []
            for i in range(4):
                ns_records_xpath = tree.xpath("//*[@id='divDNSRecords']/table[{}]/tbody/tr".format(i))
                for table_row in ns_records_xpath:
                    row = table_row.xpath('td/text()')
                    if row[0] == 'A':
                        # for getting address, use child lookup
                        address = table_row.xpath('td/a/text()')
                        address = address[0] if address else None

                        ns_records.append(
                            {
                                'type': row[0],
                                'hostname': row[1],
                                'address': address,
                                'ttl': row[2],
                                'class': row[3],
                            }
                        )

                        if save_db and Domain.objects.filter(name=ip_domain).exists():
                            ns = NSRecord()
                            ns.type = row[0]
                            ns.hostname = row[1]
                            ns.address = address
                            ns.ttl = row[2]
                            ns.ns_class = row[3]
                            ns.save()
                            domain_info.nameserver_record.add(ns)

                    elif row[0] == 'AAAA':
                        # for getting address, use child lookup
                        ns_records.append(
                            {
                                'type': row[0],
                                'hostname': row[1],
                                'address': row[2],
                                'ttl': row[3],
                                'class': row[4],
                            }
                        )

                        if save_db and Domain.objects.filter(name=ip_domain).exists():
                            ns = NSRecord()
                            ns.type = row[0]
                            ns.hostname = row[1]
                            ns.address = row[2]
                            ns.ttl = row[3]
                            ns.ns_class = row[4]
                            ns.save()
                            domain_info.nameserver_record.add(ns)

                    elif row[0] == 'MX':
                        ns_records.append(
                            {
                                'type': row[0],
                                'hostname': row[1],
                                'address': row[2],
                                'preference': row[3],
                                'ttl': row[4],
                                'class': row[5],
                            }
                        )

                        if save_db and Domain.objects.filter(name=ip_domain).exists():
                            ns = NSRecord()
                            ns.type = row[0]
                            ns.hostname = row[1]
                            ns.address = address
                            ns.preference = row[3]
                            ns.ttl = row[4]
                            ns.ns_class = row[5]
                            ns.save()
                            domain_info.nameserver_record.add(ns)


            final_organization_association_url = 'https://domainbigdata.com' + organization_association_href if organization_association_href else None
            final_email_association_url = 'https://domainbigdata.com' + email_association_href if email_association_href else None


            return {
                'status': True,
                'ip_domain': ip_domain,
                'domain': {
                    'date_created': date_created,
                    'domain_age': domain_age,
                    'ip_address': ip_address,
                    'geolocation': geolocation,
                    'geolocation_iso': geolocation_iso,
                },
                'nameserver': {
                    'history': dns_history,
                    'records': ns_records
                },
                'registrant': {
                    'name': name,
                    'organization': organization,
                    'email': email,
                    'address': address,
                    'city': city,
                    'state': state,
                    'country': country,
                    'country_iso': country_iso,
                    'tel': tel,
                    'fax': fax,
                    'organization_association_url': final_organization_association_url,
                    'email_association_url': final_email_association_url,
                },
                'related_domains': unique_associated_domains,
                'related_tlds': related_tlds,
                'whois': whois if whois else None
            }
        except Exception as e:
            logging.exception(e)
            return {
                'status': False,
                'ip_domain': ip_domain,
                'result': 'Domain not found'
            }
    elif ip_domain and fetch_from_db:
        if Domain.objects.filter(name=ip_domain).exists():
            domain = Domain.objects.get(name=ip_domain)
            unique_associated_domains = []

            if domain.domain_info and domain.domain_info.associated_domains:
                unique_associated_domains = [d.name for d in domain.domain_info.associated_domains.all()]


            unique_related_tlds = []
            if domain.domain_info and domain.domain_info.related_tlds:
                unique_related_tlds = [d.name for d in domain.domain_info.related_tlds.all()]

            if domain.domain_info:
                return {
                    'status': True,
                    'ip_domain': ip_domain,
                    'domain': {
                        'date_created': domain.domain_info.date_created,
                        'domain_age': domain.domain_info.domain_age,
                        'ip_address': domain.domain_info.ip_address,
                        'geolocation': domain.domain_info.geolocation,
                        'geolocation_iso': domain.domain_info.geolocation_iso,
                    },
                    'nameserver': {
                        'history': NameServerHistorySerializer(domain.domain_info.nameserver_history.all(), many=True).data,
                        'records': NSRecordSerializer(domain.domain_info.nameserver_record.all(), many=True).data
                    },
                    'registrant': {
                        'name': domain.domain_info.whois.registrant.name,
                        'organization': domain.domain_info.whois.registrant.organization,
                        'email': domain.domain_info.whois.registrant.email,
                        'address': domain.domain_info.whois.registrant.address,
                        'city': domain.domain_info.whois.registrant.city,
                        'state': domain.domain_info.whois.registrant.state,
                        'country': domain.domain_info.whois.registrant.country,
                        'country_iso': domain.domain_info.whois.registrant.country_iso,
                        'tel': domain.domain_info.whois.registrant.phone_number,
                        'fax': domain.domain_info.whois.registrant.fax,
                    },
                    'related_domains': unique_associated_domains,
                    'related_tlds': unique_related_tlds,
                    'whois': domain.domain_info.whois.details
                }
            return {
                'status': False,
                'message': 'WHOIS does not exist.'
            }
        return {
            'status': False,
            'message': 'Domain ' + ip_domain + ' does not exist as target and could not fetch WHOIS from database.'
        }

def calculate_age(created):
    today = date.today()
    return today.year - created.year - ((today.month, today.day) < (created.month, created.day))

def return_zeorth_if_list(variable):
    return variable[0] if type(variable) == list else variable

def get_whois(ip_domain, save_db=False, fetch_from_db=True):
    if ip_domain and not fetch_from_db:

        try:
            result = asyncwhois.whois_domain(ip_domain)
            whois = result.parser_output
            if not whois.get('domain_name'):
                raise Exception
        except Exception as e:
            logger.error(e)
            return {
            'status': False,
            'ip_domain': ip_domain,
            'result': 'Invalid Domain/IP, WHOIS could not be fetched from WHOIS database'
            }

        created = whois.get('created')
        expires = whois.get('expires')
        updated = whois.get('updated')

        registrar = whois.get('registrar')
        dnssec = whois.get('dnssec')
        status = whois.get('status')

        registrant_name = whois.get('registrant_name')
        registrant_organization = whois.get('registrant_organization')
        registrant_address = whois.get('registrant_address')
        registrant_city = whois.get('registrant_city')
        registrant_state = whois.get('registrant_state')
        registrant_zipcode = whois.get('registrant_zipcode')
        registrant_country = whois.get('registrant_country')
        registrant_email = whois.get('registrant_email')
        registrant_phone = whois.get('registrant_phone')
        registrant_fax = whois.get('registrant_fax')

        name_servers = whois.get('name_servers')

        admin_name = whois.get('admin_name')
        admin_id = whois.get('admin_id')
        admin_organization = whois.get('admin_organization')
        admin_city = whois.get('admin_city')
        admin_address = whois.get('admin_address')
        admin_state = whois.get('admin_state')
        admin_zipcode = whois.get('admin_zipcode')
        admin_country = whois.get('admin_country')
        admin_phone = whois.get('admin_phone')
        admin_fax = whois.get('admin_fax')
        admin_email = whois.get('admin_email')

        tech_name = whois.get('tech_name')
        tech_id = whois.get('tech_id')
        tech_organization = whois.get('tech_organization')
        tech_city = whois.get('tech_city')
        tech_address = whois.get('tech_address')
        tech_state = whois.get('tech_state')
        tech_zipcode = whois.get('tech_zipcode')
        tech_country = whois.get('tech_country')
        tech_phone = whois.get('tech_phone')
        tech_fax = whois.get('tech_fax')
        tech_email = whois.get('tech_email')

        if save_db and Domain.objects.filter(name=ip_domain).exists():
            logger.info('Saving in DB!')
            domain = Domain.objects.get(name=ip_domain)

            domain_info = DomainInfo()
            domain_info.raw_text = result.query_output.strip()
            domain_info.dnsec = dnssec
            domain_info.created = created
            domain_info.updated = updated
            domain_info.expires = expires

            # registrant
            domain_info.registrar = DomainRegistrar.objects.get_or_create(
                name=registrar
            )[0] if registrar else None

            domain_info.registrant_name = DomainRegisterName.objects.get_or_create(
                name=registrant_name
            )[0] if registrant_name else None
            domain_info.registrant_organization = DomainRegisterOrganization.objects.get_or_create(
                name=registrant_organization
            )[0] if registrant_organization else None
            domain_info.registrant_address = DomainAddress.objects.get_or_create(
                name=registrant_address
            )[0] if registrant_address else None
            domain_info.registrant_city = DomainCity.objects.get_or_create(
                name=registrant_city
            )[0] if registrant_city else None
            domain_info.registrant_state = DomainState.objects.get_or_create(
                name=registrant_state
            )[0] if registrant_state else None
            domain_info.registrant_zip_code = DomainZipCode.objects.get_or_create(
                name=registrant_zipcode
            )[0] if registrant_zipcode else None
            domain_info.registrant_country = DomainCountry.objects.get_or_create(
                name=registrant_country
            )[0] if registrant_country else None
            domain_info.registrant_email = DomainEmail.objects.get_or_create(
                name=re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", registrant_email).group()
            )[0] if re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", registrant_email) else None
            domain_info.registrant_phone = DomainPhone.objects.get_or_create(
                name=registrant_phone
            )[0] if registrant_phone else None
            domain_info.registrant_fax = DomainFax.objects.get_or_create(
                name=registrant_fax
            )[0] if registrant_fax else None

            # admin
            domain_info.admin_name = DomainRegisterName.objects.get_or_create(
                name=admin_name
            )[0] if admin_name else None
            domain_info.admin_id = DomainRegistrarID.objects.get_or_create(
                name=admin_id
            )[0] if admin_id else None
            domain_info.admin_organization = DomainRegisterOrganization.objects.get_or_create(
                name=admin_organization
            )[0] if admin_organization else None
            domain_info.admin_address = DomainAddress.objects.get_or_create(
                name=admin_address
            )[0] if admin_address else None
            domain_info.admin_city = DomainCity.objects.get_or_create(
                name=admin_city
            )[0] if admin_city else None
            domain_info.admin_state = DomainState.objects.get_or_create(
                name=admin_state
            )[0] if admin_state else None
            domain_info.admin_zip_code = DomainZipCode.objects.get_or_create(
                name=admin_zipcode
            )[0] if admin_zipcode else None
            domain_info.admin_country = DomainCountry.objects.get_or_create(
                name=admin_country
            )[0] if admin_country else None
            domain_info.admin_email = DomainEmail.objects.get_or_create(
                name=re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", admin_email).group()
            )[0] if re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", admin_email) else None
            domain_info.admin_phone = DomainPhone.objects.get_or_create(
                name=admin_phone
            )[0] if admin_phone else None
            domain_info.admin_fax = DomainFax.objects.get_or_create(
                name=admin_fax
            )[0] if admin_fax else None

            # tech
            domain_info.tech_name = DomainRegisterName.objects.get_or_create(
                name=tech_name
            )[0] if tech_name else None
            domain_info.tech_id = DomainRegistrarID.objects.get_or_create(
                name=tech_id
            )[0] if tech_id else None
            domain_info.tech_organization = DomainRegisterOrganization.objects.get_or_create(
                name=tech_organization
            )[0] if tech_organization else None
            domain_info.tech_address = DomainAddress.objects.get_or_create(
                name=tech_address
            )[0] if tech_address else None
            domain_info.tech_city = DomainCity.objects.get_or_create(
                name=tech_city
            )[0] if tech_city else None
            domain_info.tech_state = DomainState.objects.get_or_create(
                name=tech_state
            )[0] if tech_state else None
            domain_info.tech_zip_code = DomainZipCode.objects.get_or_create(
                name=tech_zipcode
            )[0] if tech_zipcode else None
            domain_info.tech_country = DomainCountry.objects.get_or_create(
                name=tech_country
            )[0] if tech_country else None
            domain_info.tech_email = DomainEmail.objects.get_or_create(
                name=re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", tech_email).group()
            )[0] if re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", tech_email) else None
            domain_info.tech_phone = DomainPhone.objects.get_or_create(
                name=tech_phone
            )[0] if tech_phone else None
            domain_info.tech_fax = DomainFax.objects.get_or_create(
                name=tech_fax
            )[0] if tech_fax else None

            domain_info.save()

            # status
            for _status in status:
                domain_info.status.add(
                    DomainWhoisStatus.objects.get_or_create(
                        status=_status
                )[0])

            # name servers
            for name_server in name_servers:
                domain_info.name_servers.add(
                    NameServers.objects.get_or_create(
                        name=name_server
                )[0])

            domain.domain_info = domain_info
            domain.save()
        return {
            'status': True,
            'ip_domain': ip_domain,
            'domain': {
                'created': created,
                'updated': updated,
                'expires': expires,
                'registrar': registrar,
                'geolocation_iso': registrant_country,
                'dnssec': dnssec,
                'status': status,
            },
            'registrant': {
                'name': registrant_name,
                'organization': registrant_organization,
                'address': registrant_address,
                'city': registrant_city,
                'state': registrant_state,
                'zipcode': registrant_zipcode,
                'country': registrant_country,
                'phone': registrant_phone,
                'fax': registrant_fax,
                'email': re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", registrant_email).group() if re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", registrant_email) else None,
            },
            'admin': {
                'name': admin_name,
                'id': admin_id,
                'organization': admin_organization,
                'city': admin_city,
                'address': admin_address,
                'state': admin_state,
                'zipcode': admin_zipcode,
                'country': admin_country,
                'phone': admin_phone,
                'fax': admin_fax,
                'email': re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", admin_email).group() if re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", admin_email) else None,
            },
            'technical_contact': {
                'name': tech_name,
                'id': tech_id,
                'organization': tech_organization,
                'city': tech_city,
                'address': tech_address,
                'state': tech_state,
                'zipcode': tech_zipcode,
                'country': tech_country,
                'phone': tech_phone,
                'fax': tech_fax,
                'email': re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", tech_email).group() if re.search(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", tech_email) else None,
            },
            'nameservers': name_servers,
            'raw_text': result.query_output.strip()
        }

    elif ip_domain and fetch_from_db:
        domain = Domain.objects.get(name=ip_domain) if Domain.objects.filter(name=ip_domain).exists() else None
        if not domain:
            return {
                'status': False,
                'message': 'Domain ' + ip_domain + ' does not exist as target and could not fetch WHOIS from database.'
            }

        if not domain.domain_info:
            return {
                'status': False,
                'message': 'WHOIS could not be fetched!'
            }

        return {
            'status': True,
            'ip_domain': ip_domain,
            'domain': {
                'created': domain.domain_info.created,
                'updated': domain.domain_info.updated,
                'expires': domain.domain_info.expires,
                'registrar': DomainRegistrarSerializer(domain.domain_info.registrar).data['name'],
                'geolocation_iso': DomainCountrySerializer(domain.domain_info.registrant_country).data['name'],
                'dnssec': domain.domain_info.dnssec,
                'status': [status['status'] for status in DomainWhoisStatusSerializer(domain.domain_info.status, many=True).data]
            },
            'registrant': {
                'name': DomainRegisterNameSerializer(domain.domain_info.registrant_name).data['name'],
                'organization': DomainRegisterOrganizationSerializer(domain.domain_info.registrant_organization).data['name'],
                'address': DomainAddressSerializer(domain.domain_info.registrant_address).data['name'],
                'city': DomainCitySerializer(domain.domain_info.registrant_city).data['name'],
                'state': DomainStateSerializer(domain.domain_info.registrant_state).data['name'],
                'zipcode': DomainZipCodeSerializer(domain.domain_info.registrant_zip_code).data['name'],
                'country': DomainCountrySerializer(domain.domain_info.registrant_country).data['name'],
                'phone': DomainPhoneSerializer(domain.domain_info.registrant_phone).data['name'],
                'fax': DomainFaxSerializer(domain.domain_info.registrant_fax).data['name'],
                'email': DomainEmailSerializer(domain.domain_info.registrant_email).data['name'],
            },
            'admin': {
                'name': DomainRegisterNameSerializer(domain.domain_info.admin_name).data['name'],
                'id': DomainRegistrarIDSerializer(domain.domain_info.admin_id).data['name'],
                'organization': DomainRegisterOrganizationSerializer(domain.domain_info.admin_organization).data['name'],
                'address': DomainAddressSerializer(domain.domain_info.admin_address).data['name'],
                'city': DomainCitySerializer(domain.domain_info.admin_city).data['name'],
                'state': DomainStateSerializer(domain.domain_info.admin_state).data['name'],
                'zipcode': DomainZipCodeSerializer(domain.domain_info.admin_zip_code).data['name'],
                'country': DomainCountrySerializer(domain.domain_info.admin_country).data['name'],
                'phone': DomainPhoneSerializer(domain.domain_info.admin_phone).data['name'],
                'fax': DomainFaxSerializer(domain.domain_info.admin_fax).data['name'],
                'email': DomainEmailSerializer(domain.domain_info.admin_email).data['name'],
            },
            'technical_contact': {
                'name': DomainRegisterNameSerializer(domain.domain_info.tech_name).data['name'],
                'id': DomainRegistrarIDSerializer(domain.domain_info.tech_id).data['name'],
                'organization': DomainRegisterOrganizationSerializer(domain.domain_info.tech_organization).data['name'],
                'address': DomainAddressSerializer(domain.domain_info.tech_address).data['name'],
                'city': DomainCitySerializer(domain.domain_info.tech_city).data['name'],
                'state': DomainStateSerializer(domain.domain_info.tech_state).data['name'],
                'zipcode': DomainZipCodeSerializer(domain.domain_info.tech_zip_code).data['name'],
                'country': DomainCountrySerializer(domain.domain_info.tech_country).data['name'],
                'phone': DomainPhoneSerializer(domain.domain_info.tech_phone).data['name'],
                'fax': DomainFaxSerializer(domain.domain_info.tech_fax).data['name'],
                'email': DomainEmailSerializer(domain.domain_info.tech_email).data['name'],
            },
            'nameservers': [ns['name'] for ns in NameServersSerializer(domain.domain_info.name_servers, many=True).data],
            'raw_text': domain.domain_info.raw_text
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
