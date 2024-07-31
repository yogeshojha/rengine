import logging
import os
import unittest
import pathlib
from celery.utils.log import get_task_logger
from reNgine.settings import DEBUG
from reNgine.tasks import parse_nmap_results, parse_nmap_vuln_output, parse_nmap_vulscan_output

os.environ['RENGINE_SECRET_KEY'] = 'secret'
os.environ['CELERY_ALWAYS_EAGER'] = 'True'

logger = get_task_logger(__name__)
DOMAIN_NAME = os.environ['DOMAIN_NAME']
FIXTURES_DIR = pathlib.Path().absolute() / 'fixtures' / 'nmap_xml'

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

if not DEBUG:
    logging.disable(logging.CRITICAL)

class TestNmapParsing(unittest.TestCase):
    def setUp(self):
        self.nmap_vuln_single_xml = FIXTURES_DIR / 'nmap_vuln_single.xml'
        self.nmap_vuln_multiple_xml = FIXTURES_DIR / 'nmap_vuln_multiple.xml'
        self.nmap_vulscan_single_xml = FIXTURES_DIR / 'nmap_vulscan_single.xml'
        self.nmap_vulscan_multiple_xml = FIXTURES_DIR / 'nmap_vulscan_multiple.xml'
        self.all_xml = [
            self.nmap_vuln_single_xml,
            self.nmap_vuln_multiple_xml,
            self.nmap_vulscan_single_xml,
            self.nmap_vulscan_multiple_xml
        ]

    def test_nmap_parse(self):
        for xml_file in self.all_xml:
            vulns = parse_nmap_results(xml_file)
            self.assertGreater(len(vulns), 0)
            logging.info(f"Parsed {len(vulns)} vulnerabilities from {xml_file}")

    def test_nmap_vuln_single(self):
        logging.info("Testing nmap_vuln_single")
        # Implement test logic here

    def test_nmap_vuln_multiple(self):
        logging.info("Testing nmap_vuln_multiple")
        # Implement test logic here

    def test_nmap_vulscan_single(self):
        logging.info("Testing nmap_vulscan_single")
        # Implement test logic here

    def test_nmap_vulscan_multiple(self):
        logging.info("Testing nmap_vulscan_multiple")
        # Implement test logic here

if __name__ == '__main__':
    unittest.main()
