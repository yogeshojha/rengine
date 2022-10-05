import logging
import os
import unittest

os.environ['RENGINE_SECRET_KEY'] = 'secret'
os.environ['CELERY_ALWAYS_EAGER'] = 'True'

import yaml
from celery.utils.log import get_task_logger
from reNgine.settings import DEBUG
from reNgine.tasks import (http_crawl, port_scan, subdomain_discovery,
                           vulnerability_scan, fetch_url, dir_file_fuzz, osint, initiate_scan)
from startScan.models import *

logger = get_task_logger(__name__)
DOMAIN_NAME = os.environ['DOMAIN_NAME']
if not DEBUG:
    logging.disable(logging.CRITICAL)

class TestFullScanDefaultConfig(unittest.TestCase):
    def setUp(self):
        self.yaml_configuration = {
            'subdomain_discovery': {},
            'port_scan': {},
            'vulnerability_scan': {},
            'osint': {},
            'dir_file_fuzz': {},
            'screenshot': {}
        }
        self.domain, _ = Domain.objects.get_or_create(name=DOMAIN_NAME)
        self.subdomain = Subdomain.objects.get_or_create(name=DOMAIN_NAME, target_domain=self.domain)
        self.engine = EngineType(engine_name='test_engine', yaml_configuration=yaml.dump(self.yaml_configuration))
        self.scan = ScanHistory(domain=self.domain, scan_type=self.engine, start_scan_date=timezone.now())
        self.engine.save()
        self.scan.save()
        self.ctx = {
            'track': False,
            'yaml_configuration': self.yaml_configuration,
            'results_dir': '/tmp',
            'scan_history_id': self.scan.id,
            'engine_id': self.engine.id
        }
        self.url = f'https://{DOMAIN_NAME}'

    def tearDown(self):
        self.domain.delete()
        self.scan.delete()
        self.engine.delete()

    def test_http_crawl(self):
        results = http_crawl([DOMAIN_NAME], ctx=self.ctx)
        self.assertGreater(len(results), 0)
        self.assertIn('final-url', results[0])
        url = results[0]['final-url']
        if DEBUG:
            print(url)

    def test_subdomain_discovery(self):
        subdomains = subdomain_discovery(DOMAIN_NAME, ctx=self.ctx)
        if DEBUG:
            print(subdomains)
        self.assertTrue(subdomains is not None)
        self.assertGreater(len(subdomains), 0)

    # def test_fetch_url(self):
    #     urls = fetch_url(urls=[self.url], ctx=self.ctx)

    # def test_dir_file_fuzz(self):
    #     subdomain = Subdomain(name=DOMAIN_NAME, domain=domain)
    #     subdomain.save()
    #     urls = dir_file_fuzz(ctx=self.ctx)
    #     self.assertGreater(len(urls), 0)
    #     domain.delete()
    #     subdomain.delete()

    # def test_vulnerability_scan(self):
    #     url = f'https://{DOMAIN_NAME}'
    #     vulns = vulnerability_scan(urls=[self.url], ctx=self.ctx)
    #     self.assertTrue(vulns is not None)

    # def test_network_scan(self):
    #     subdomains = subdomain_discovery(DOMAIN_NAME, ctx=self.ctx)
    #     self.assertGreater(len(subdomains), 0)
    #     print([subdomain['name'] for subdomain in subdomains])
    #     ports = port_scan(hosts=subdomains, ctx=self.ctx)
    #     urls = []
    #     for host, ports in ports.items():
    #         print(f'Host {host} opened ports: {ports}')
    #         self.assertGreater(len(ports), 0)
    #         self.assertIn(80, ports)
    #         self.assertIn(443, ports)
    #         for port in ports:
    #             if port in [80, 443]: # http
    #                 results = http_crawl(urls=[f'{host}:{port}'])
    #                 self.assertGreater(len(results), 0)
    #                 final_url = results[0]['final-url']
    #                 urls.append(final_url)
    #     self.assertGreater(len(urls), 0)
    #     vulns = vulnerability_scan(urls=urls, ctx=self.ctx)

    # def test_initiate_scan(self):
    #     scan = ScanHistory()
    #     domain = Domain(name=DOMAIN_NAME)
    #     domain.save()
    #     subdomain = Subdomain(name=DOMAIN_NAME, domain=domain)
    #     subdomain.save()