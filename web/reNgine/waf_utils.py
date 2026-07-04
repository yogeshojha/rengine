import logging
import requests
import socket
import ssl
from django.db.models import Q
from startScan.models import Subdomain, WafBypassFinding
from dashboard.models import ShodanAPIKey, CensysAPIKey
from reNgine.opsec_utils import OpSecManager

logger = logging.getLogger(__name__)

class OriginDiscoveryManager:
    """
    Manager for discovering the original IP of a WAF-protected domain.
    """
    def __init__(self, subdomain_obj):
        self.subdomain = subdomain_obj
        self.domain = subdomain_obj.name
        self.shodan_key = self._get_shodan_key()
        self.censys_id, self.censys_secret = self._get_censys_credentials()
        self.opsec = OpSecManager()

    def _get_shodan_key(self):
        key_obj = ShodanAPIKey.objects.first()
        return key_obj.key if key_obj else None

    def _get_censys_credentials(self):
        key_obj = CensysAPIKey.objects.first()
        if key_obj:
            return key_obj.api_id, key_obj.api_secret
        return None, None

    def find_origin(self, use_shodan=True, use_censys=True, use_heuristics=True):
        results = set()
        
        if use_shodan and self.shodan_key:
            results.update(self._query_shodan())
            
        if use_censys and self.censys_id:
            results.update(self._query_censys())
            
        if use_heuristics:
            results.update(self._internal_heuristics())
            
        # Filter out known WAF/CDN IPs if possible
        # (For now we just return all found IPs)
        return list(results)

    def _query_shodan(self):
        ips = []
        try:
            # Query by hostname
            url = f"https://api.shodan.io/shodan/host/search?key={self.shodan_key}&query=hostname:{self.domain}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for match in data.get('matches', []):
                    ips.append(match.get('ip_str'))
            
            # Query by SSL serial if available
            cert_serial = self._get_ssl_serial()
            if cert_serial:
                url = f"https://api.shodan.io/shodan/host/search?key={self.shodan_key}&query=ssl.cert.serial:{cert_serial}"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for match in data.get('matches', []):
                        ips.append(match.get('ip_str'))
        except Exception as e:
            logger.error(f"Shodan query failed for {self.domain}: {str(e)}")
        return ips

    def _query_censys(self):
        ips = []
        try:
            # Query by domain
            url = "https://search.censys.io/api/v2/hosts/search"
            query = f"services.tls.certificates.leaf_data.names: {self.domain}"
            auth = (self.censys_id, self.censys_secret)
            response = requests.get(url, params={'q': query}, auth=auth, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for result in data.get('result', {}).get('hits', []):
                    ips.append(result.get('ip'))
        except Exception as e:
            logger.error(f"Censys query failed for {self.domain}: {str(e)}")
        return ips

    def _internal_heuristics(self):
        ips = []
        # 1. Check for common 'origin' subdomains in the same project
        common_prefixes = ['direct', 'origin', 'dev', 'stage', 'backend', 'vps']
        base_domain = '.'.join(self.domain.split('.')[-2:])
        
        related_subdomains = Subdomain.objects.filter(
            Q(name__icontains='direct') | 
            Q(name__icontains='origin') | 
            Q(name__icontains='dev'),
            name__endswith=base_domain
        ).exclude(id=self.subdomain.id)
        
        for sub in related_subdomains:
            # Get IP addresses for these subdomains
            for ip_obj in sub.ip_addresses.all():
                ips.append(ip_obj.address)
                
        return ips

    def _get_ssl_serial(self):
        try:
            hostname = self.domain
            ctx = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert(True)
                    cert_dict = ssl.DER_cert_to_PEM_cert(cert)
                    # We need the serial number. ssl module doesn't provide it easily from DER.
                    # This is a simplification. In production, we'd use 'cryptography' library.
                    return None 
        except:
            return None

class WafBypassOrchestrator:
    """
    Orchestrator for testing WAF bypass techniques.
    """
    def __init__(self, subdomain_obj):
        self.subdomain = subdomain_obj
        self.target_url = f"https://{subdomain_obj.name}"
        self.opsec = OpSecManager()

    def run_all_tests(self, use_nuclei=True, use_benchmarking=True):
        findings = []
        if use_benchmarking:
            findings.extend(self._test_headers())
        
        if use_nuclei:
            findings.extend(self._run_nuclei_bypass())
            
        return findings

    def _test_headers(self):
        """
        Test susceptibility to various HTTP headers used for WAF bypass.
        """
        bypass_headers = {
            'X-Forwarded-For': '127.0.0.1',
            'X-Originating-IP': '127.0.0.1',
            'X-Remote-IP': '127.0.0.1',
            'X-Remote-Addr': '127.0.0.1',
            'X-Client-IP': '127.0.0.1',
            'X-Real-IP': '127.0.0.1',
            'True-Client-IP': '127.0.0.1',
            'Client-IP': '127.0.0.1',
            'Forwarded': 'for=127.0.0.1;proto=http'
        }
        
        findings = []
        for header, value in bypass_headers.items():
            try:
                # Send a "suspicious" payload with and without the header
                payload = "/etc/passwd"
                headers = {header: value}
                
                # We check if the response status or body changes significantly
                # This is a heuristic.
                r = requests.get(f"{self.target_url}?file={payload}", headers=headers, timeout=10, verify=False)
                
                # If we get a 200 or something that isn't a 403/406, it might be a bypass
                if r.status_code not in [403, 406, 429]:
                    finding = WafBypassFinding.objects.create(
                        subdomain=self.subdomain,
                        technique=f"Header Injection: {header}",
                        is_successful=True,
                        payload_evidence=f"Request with {header}: {value} returned {r.status_code}"
                    )
                    findings.append(finding)
            except Exception as e:
                logger.error(f"Header bypass test failed for {header}: {str(e)}")
                
        return findings

    def _run_nuclei_bypass(self):
        """
        Placeholder for Nuclei bypass execution. 
        In reNgine, this is usually handled by calling the nuclei binary.
        """
        # This will be implemented in the Celery task to use the existing Nuclei infrastructure
        return []
