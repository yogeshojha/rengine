import os
import random
import logging
import re
import tempfile
import subprocess
from scanEngine.models import OpSec, Proxy
from reNgine.definitions import MEDUSA_EXEC_PATH, PROXYCHAINS_EXEC_PATH

class OpSecManager:
    """
    Manages Operational Security (OpSec) settings and provides utility functions
    to inject stealth flags into tool commands.
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.2; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    ]

    WAF_BYPASS_HEADERS = [
        "X-Forwarded-For: 127.0.0.1",
        "X-Originating-IP: 127.0.0.1",
        "X-Remote-IP: 127.0.0.1",
        "X-Remote-Addr: 127.0.0.1",
        "X-Client-IP: 127.0.0.1",
        "X-Host: 127.0.0.1",
        "Forwarded: for=127.0.0.1;proto=http;by=127.0.0.1",
    ]

    def __init__(self):
        self.settings = OpSec.objects.first()
        self.proxy_settings = Proxy.objects.first()

    def is_enabled(self):
        return self.settings and self.settings.enable_opsec

    def get_random_ua(self):
        return random.choice(self.USER_AGENTS)

    def get_waf_headers(self):
        return self.WAF_BYPASS_HEADERS

    def apply_stealth(self, tool_name, command):
        """
        Applies stealth flags to a given command string for a specific tool.
        """
        if not self.is_enabled():
            return command

        if tool_name == "nuclei":
            return self._apply_nuclei(command)
        elif tool_name == "nmap":
            return self._apply_nmap(command)
        elif tool_name == "subfinder":
            return self._apply_subfinder(command)
        elif tool_name == "amass":
            return self._apply_amass(command)
        elif tool_name == "ffuf":
            return self._apply_ffuf(command)
        elif tool_name == "httpx":
            return self._apply_httpx(command)
        
        return command

    def _apply_nuclei(self, cmd):
        flags = []
        if self.settings.enable_random_ua:
            flags.append(f"-H 'User-Agent: {self.get_random_ua()}'")
        
        if self.settings.enable_waf_bypass:
            for header in self.get_waf_headers():
                flags.append(f"-H '{header}'")
        
        if self.settings.enable_rate_limit:
            flags.append(f"-rl {self.settings.max_rps}")
        
        if self.settings.http_protocol == "http2":
            flags.append("-h2")
        
        if self.settings.custom_dns_servers:
            dns = ",".join(self.settings.custom_dns_servers.splitlines())
            flags.append(f"-resolvers {dns}")

        return f"{cmd} {' '.join(flags)}"

    def _apply_nmap(self, cmd):
        flags = []
        if self.settings.enable_delay:
            flags.append(f"--scan-delay {self.settings.delay_ms}ms")
        
        if self.settings.enable_random_ua:
            flags.append(f"--script-args http.useragent='{self.get_random_ua()}'")
        
        if self.settings.custom_dns_servers:
            dns = ",".join(self.settings.custom_dns_servers.splitlines())
            flags.append(f"--dns-servers {dns}")

        return f"{cmd} {' '.join(flags)}"

    def _apply_subfinder(self, cmd):
        flags = []
        if self.settings.enable_rate_limit:
            # subfinder -rl (requests per minute)
            flags.append(f"-rl {self.settings.max_rps * 60}")
        return f"{cmd} {' '.join(flags)}"

    def _apply_amass(self, cmd):
        return cmd

    def _apply_ffuf(self, cmd):
        flags = []
        if self.settings.enable_random_ua:
            flags.append(f"-H 'User-Agent: {self.get_random_ua()}'")
        if self.settings.enable_rate_limit:
            flags.append(f"-p {1.0 / self.settings.max_rps}")
        return f"{cmd} {' '.join(flags)}"

    def _apply_httpx(self, cmd):
        flags = []
        if self.settings.enable_random_ua:
            flags.append(f"-H 'User-Agent: {self.get_random_ua()}'")
        if self.settings.http_protocol == "http2":
            flags.append("-http2")
        return f"{cmd} {' '.join(flags)}"

    def strip_metadata(self, file_path):
        """
        Strips metadata from a given file. Supported formats: PDF, JPG, PNG.
        """
        if not self.is_enabled() or not self.settings.enable_metadata_stripping:
            return

        if not os.path.exists(file_path):
            return

        ext = os.path.splitext(file_path)[1].lower()
        try:
            if ext == ".pdf":
                import pikepdf
                with pikepdf.open(file_path, allow_overwriting_input=True) as pdf:
                    del pdf.Root.Metadata
                    pdf.save(file_path)
            elif ext in [".jpg", ".jpeg", ".png"]:
                from PIL import Image
                img = Image.open(file_path)
                data = list(img.getdata())
                img_without_exif = Image.new(img.mode, img.size)
                img_without_exif.putdata(data)
                img_without_exif.save(file_path)
        except Exception:
            pass

    def strip_directory(self, directory):
        """
        Recursively strips metadata from all files in a directory.
        """
        if not self.is_enabled() or not self.settings.enable_metadata_stripping:
            return
        

class ProxychainsWrapper:
    """
    Handles dynamic generation of proxychains configurations for stealthy rotation.
    """
    def __init__(self):
        self.proxies = self._fetch_proxies()

    def _fetch_proxies(self):
        proxy_obj = Proxy.objects.first()
        if not proxy_obj or not proxy_obj.use_proxy or not proxy_obj.proxies:
            return []
        
        # Clean and validate proxy list
        proxies = []
        for line in proxy_obj.proxies.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Format expected by proxychains: type host port [user pass]
            # reNgine might store as protocol://host:port or host:port
            
            p_type = "socks5" # default
            p_host = ""
            p_port = ""
            
            if "://" in line:
                p_type = line.split("://")[0].lower()
                if p_type == "http" or p_type == "https":
                    p_type = "http" # proxychains uses 'http' for both
                line = line.split("://")[1]
            
            if ":" in line:
                parts = line.split(":")
                p_host = parts[0]
                p_port = parts[1]
                # If there are more parts, could be user:pass@host:port or host:port:user:pass
                # But simple host:port is most common in reNgine
                proxies.append(f"{p_type} {p_host} {p_port}")
            elif " " in line:
                # Already in type host port format
                proxies.append(line)
                
        return proxies

    def get_random_proxy(self):
        return random.choice(self.proxies) if self.proxies else None

    def write_temp_config(self, proxy_str):
        fd, path = tempfile.mkstemp(suffix=".conf", prefix="proxychains_")
        os.close(fd)
        with open(path, 'w') as f:
            f.write("strict_chain\n")
            f.write("proxy_dns\n")
            f.write("tcp_read_time_out 15000\ntcp_connect_time_out 8000\n")
            f.write("[ProxyList]\n")
            f.write(f"{proxy_str}\n")
        return path


class BruteForceOrchestrator:
    """
    Orchestrates Medusa brute-force attacks with proxy rotation and stealth.
    """
    def __init__(self, target, service, port=None, users=[], passwords=[]):
        self.target = target
        self.service = service
        self.port = port
        self.users = users
        self.passwords = passwords
        self.proxy_manager = ProxychainsWrapper()
        self.results = []
        self.total_attempts = 0
        self.total_success = 0
        self.logger = logging.getLogger(__name__)

    def _generate_combos(self):
        combos = []
        for user in self.users:
            for password in self.passwords:
                combos.append((user, password))
        random.shuffle(combos)
        return combos

    def run(self, min_attempts=1, max_attempts=10, stop_on_success=True):
        combos = self._generate_combos()
        i = 0
        while i < len(combos):
            # Determine batch size (1-10 attempts)
            batch_size = random.randint(min_attempts, max_attempts)
            batch = combos[i:i+batch_size]
            i += batch_size

            # Create temp combo file for Medusa
            fd, combo_file = tempfile.mkstemp(suffix=".txt", prefix="medusa_combo_")
            os.close(fd)
            # Clean target for Medusa (strip protocol and port if present)
            clean_target = self.target.split("://")[-1].split(":")[0]
            
            # Medusa combo file format: host:user:pass
            batch_data = [f"{clean_target}:{c[0]}:{c[1]}" for c in batch]
            
            with open(combo_file, 'w') as f:
                f.write("\n".join(batch_data))

            # Setup proxy
            proxy = self.proxy_manager.get_random_proxy()
            cmd_prefix = ""
            conf_path = None
            if proxy:
                conf_path = self.proxy_manager.write_temp_config(proxy)
                cmd_prefix = f"{PROXYCHAINS_EXEC_PATH} -f {conf_path} "

            # Build Medusa command
            # -h host, -n port, -M service, -C combo_file, -O output
            port_flag = f"-n {self.port}" if self.port else ""
            ssl_flag = "-s" if (str(self.port) == "443" or self.target.startswith("https")) else ""
            output_file = f"/tmp/medusa_{clean_target}_{random.randint(1000,9999)}.log"
            
            medusa_cmd = f"{cmd_prefix}{MEDUSA_EXEC_PATH} -h {clean_target} {port_flag} {ssl_flag} -M {self.service} -C {combo_file} -O {output_file}"
            self.logger.info(f"Executing brute-force batch: {medusa_cmd}")
            
            try:
                subprocess.run(medusa_cmd, shell=True, timeout=300)
                self.total_attempts += len(batch)
                
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        output = f.read()
                        # Medusa success pattern: "ACCOUNT FOUND"
                        if "ACCOUNT FOUND" in output:
                            # Medusa output can vary. v2.2 format:
                            # ACCOUNT FOUND: [http] Host: 155.93.231.106 User: cisco Password: apo-summicron [SUCCESS]
                            # Older/Other format might have brackets: User: [user] Password: [pass]
                            found = re.findall(r"ACCOUNT FOUND: \[(.*?)\](?: Host: .*?)? User: (?:\[)?(.*?)(?:\])? Password: (?:\[)?(.*?)(?:\])?(?: \[SUCCESS\]|$)", output)
                            batch_success = 0
                            for match in found:
                                self.results.append({
                                    'user': match[1],
                                    'password': match[2],
                                    'target': self.target,
                                    'service': self.service
                                })
                                batch_success += 1
                                self.total_success += 1
                            
                            self.logger.info(f"Batch completed on {self.target}. Results: {batch_success} success, {len(batch) - batch_success} failed.")
                            
                            if stop_on_success:
                                self.logger.info(f"Success found. Stopping brute-force for {self.target}.")
                                break
                        else:
                            self.logger.info(f"Batch completed on {self.target}. All {len(batch)} attempts failed.")
            except Exception as e:
                self.logger.error(f"Error during brute-force batch execution on {self.target}: {str(e)}")
            finally:
                if os.path.exists(combo_file): os.remove(combo_file)
                if conf_path and os.path.exists(conf_path): os.remove(conf_path)
                if os.path.exists(output_file): os.remove(output_file)

        self.logger.info(f"Brute-force scan finished for {self.target}. Total Attempts: {self.total_attempts}, Total Success: {self.total_success}")
        return self.results
