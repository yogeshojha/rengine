import json
import logging
import os
import unittest

os.environ['RENGINE_SECRET_KEY'] = 'secret'
os.environ['CELERY_ALWAYS_EAGER'] = 'True'

import yaml
from celery.utils.log import get_task_logger
from reNgine.settings import DEBUG
from reNgine.tasks import (dir_file_fuzz, fetch_url, http_crawl, initiate_scan,
                           osint, port_scan, subdomain_discovery,
                           vulnerability_scan)
from startScan.models import *

logger = get_task_logger(__name__)
DOMAIN_NAME = os.environ['DOMAIN_NAME']
# if not DEBUG:
#     logging.disable(logging.CRITICAL)


class TestOnlineScan(unittest.TestCase):
    def setUp(self):
        self.url = f'https://{DOMAIN_NAME}'
        self.yaml_configuration = {
            'subdomain_discovery': {},
            'port_scan': {},
            'vulnerability_scan': {},
            'osint': {},
            'fetch_url': {},
            'dir_file_fuzz': {},
            'screenshot': {}
        }
        self.domain, _ = Domain.objects.get_or_create(name=DOMAIN_NAME)
        self.engine = EngineType(
            engine_name='test_engine',
            yaml_configuration=yaml.dump(self.yaml_configuration))
        self.engine.save()
        self.scan = ScanHistory(
            domain=self.domain,
            scan_type=self.engine,
            start_scan_date=timezone.now())
        self.scan.save()
        self.endpoint, _ = EndPoint.objects.get_or_create(
            scan_history=self.scan,
            target_domain=self.domain,
            http_url=self.url)
        self.subdomain, _ = Subdomain.objects.get_or_create(
            name=DOMAIN_NAME,
            target_domain=self.domain,
            scan_history=self.scan,
            http_url=self.url)

        self.ctx = {
            'track': False,
            'yaml_configuration': self.yaml_configuration,
            'results_dir': '/tmp',
            'scan_history_id': self.scan.id,
            'engine_id': self.engine.id
        }

    def tearDown(self):
        self.domain.delete()
        self.subdomain.delete()
        self.endpoint.delete()
        self.scan.delete()
        self.engine.delete()

    def test_http_crawl(self):
        results = http_crawl([DOMAIN_NAME], ctx=self.ctx)
        self.assertGreater(len(results), 0)
        self.assertIn('final_url', results[0])
        url = results[0]['final_url']
        if DEBUG:
            print(url)

    def test_subdomain_discovery(self):
        domain = DOMAIN_NAME.lstrip('rengine.')
        subdomains = subdomain_discovery(domain, ctx=self.ctx)
        if DEBUG:
            print(json.dumps(subdomains, indent=4))
        self.assertTrue(subdomains is not None)
        self.assertGreater(len(subdomains), 0)

    def test_fetch_url(self):
        urls = fetch_url(urls=[self.url], ctx=self.ctx)
        if DEBUG:
            print(urls)
        self.assertGreater(len(urls), 0)

    # def test_dir_file_fuzz(self):
    #     urls = dir_file_fuzz(ctx=self.ctx)
    #     self.assertGreater(len(urls), 0)

    def test_vulnerability_scan(self):
        vulns = vulnerability_scan(urls=[self.url], ctx=self.ctx)
        if DEBUG:
            print(json.dumps(vulns, indent=4))
        self.assertTrue(vulns is not None)

    def test_network_scan(self):
        subdomains = subdomain_discovery(DOMAIN_NAME, ctx=self.ctx)
        self.assertGreater(len(subdomains), 0)
        host = subdomains[0]['name']
        ports = port_scan(hosts=[host], ctx=self.ctx)
        urls = []
        for host, ports in ports.items():
            print(f'Host {host} opened ports: {ports}')
            self.assertGreater(len(ports), 0)
            self.assertIn(80, ports)
            self.assertIn(443, ports)
            for port in ports:
                if port in [80, 443]: # http
                    results = http_crawl(urls=[f'{host}:{port}'])
                    self.assertGreater(len(results), 0)
                    final_url = results[0]['final_url']
                    urls.append(final_url)
        self.assertGreater(len(urls), 0)
        vulns = vulnerability_scan(urls=urls, ctx=self.ctx)

    # def test_initiate_scan(self):
    #     scan = ScanHistory()
    #     domain = Domain(name=DOMAIN_NAME)
    #     domain.save()
    #     subdomain = Subdomain(name=DOMAIN_NAME, domain=domain)
    #     subdomain.save()