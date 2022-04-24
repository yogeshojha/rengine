#!/usr/bin/python
import logging

###############################################################################
# TOOLS DEFINITIONS
###############################################################################
logger = logging.getLogger('django')

###############################################################################
# TOOLS DEFINITIONS
###############################################################################

NUCLEI_TEMPLATES_PATH = '/root/nuclei-templates/'
###############################################################################
# YAML CONFIG DEFINITIONS
###############################################################################

ALL = 'all'

SUBDOMAIN_DISCOVERY = 'subdomain_discovery'
PORT_SCAN = 'port_scan'
SCREENSHOT = 'screenshot'
DIR_FILE_FUZZ = 'dir_file_fuzz'
FETCH_URL = 'fetch_url'
INTENSITY = 'intensity'

USES_TOOLS = 'uses_tools'
THREADS = 'threads'
AMASS_WORDLIST = 'amass_wordlist'
NAABU_RATE = 'rate'
PORT = 'port'
PORTS = 'ports'
EXCLUDE_PORTS = 'exclude_ports'

EXTENSIONS = 'extensions'
USE_EXTENSIONS = 'use_extensions'
EXCLUDE_EXTENSIONS = 'exclude_extensions'
STOP_ON_ERROR = 'stop_on_error'
DELAY = 'delay'
MATCH_HTTP_STATUS = 'match_http_status'
AUTO_CALIBRATION = 'auto_calibration'
FOLLOW_REDIRECT = 'follow_redirect'

RECURSIVE = 'recursive'
RECURSIVE_LEVEL = 'recursive_level'
WORDLIST = 'wordlist'

TIMEOUT = 'timeout'
MAX_TIME = 'max_time'
EXCLUDED_SUBDOMAINS = 'excluded_subdomains'
EXCLUDE_TEXT = 'exclude_text'
IGNORE_FILE_EXTENSION = 'ignore_file_extension'
GF_PATTERNS = 'gf_patterns'

VULNERABILITY_SCAN = 'vulnerability_scan'
CUSTOM_NUCLEI_TEMPLATE = 'custom_templates'
NUCLEI_TEMPLATE = 'templates'
NUCLEI_SEVERITY = 'severity'
NUCLEI_CONCURRENCY = 'concurrency'
RATE_LIMIT = 'rate_limit'
RETRIES = 'retries'

OSINT = 'osint'
OSINT_DOCUMENTS_LIMIT = 'documents_limit'
OSINT_DISCOVER = 'discover'
OSINT_DORK = 'dork'

USE_AMASS_CONFIG = 'use_amass_config'
USE_SUBFINDER_CONFIG = 'use_subfinder_config'
USE_NUCLEI_CONFIG = 'use_nuclei_config'
USE_NAABU_CONFIG = 'use_naabu_config'

CUSTOM_HEADER = 'custom_header'

###############################################################################
# Wordlist DEFINITIONS
###############################################################################
AMASS_DEFAULT_WORDLIST_PATH = 'wordlist/default_wordlist/deepmagic.com-prefixes-top50000.txt'


###############################################################################
# Logger DEFINITIONS
###############################################################################

CONFIG_FILE_NOT_FOUND = 'Config file not found'

###############################################################################
# Preferences DEFINITIONS
###############################################################################

SMALL = '100px'
MEDIM = '200px'
LARGE = '400px'
XLARGE = '500px'

###############################################################################
# Interesting Subdomain DEFINITIONS
###############################################################################
MATCHED_SUBDOMAIN = 'Subdomain'
MATCHED_PAGE_TITLE = 'Page Title'

###############################################################################
# Celery Task Status CODES
###############################################################################
INITIATED_TASK = -1
FAILED_TASK = 0
RUNNING_TASK = 1
SUCCESS_TASK = 2
ABORTED_TASK = 3
###############################################################################
# Uncommon Ports
# Source: https://github.com/six2dez/reconftw/blob/main/reconftw.cfg
###############################################################################
UNCOMMON_WEB_PORTS = [
    81,
    300,
    591,
    593,
    832,
    981,
    1010,
    1311,
    1099,
    2082,
    2095,
    2096,
    2480,
    3000,
    3128,
    3333,
    4243,
    4567,
    4711,
    4712,
    4993,
    5000,
    5104,
    5108,
    5280,
    5281,
    5601,
    5800,
    6543,
    7000,
    7001,
    7396,
    7474,
    8000,
    8001,
    8008,
    8014,
    8042,
    8060,
    8069,
    8080,
    8081,
    8083,
    8088,
    8090,
    8091,
    8095,
    8118,
    8123,
    8172,
    8181,
    8222,
    8243,
    8280,
    8281,
    8333,
    8337,
    8443,
    8500,
    8834,
    8880,
    8888,
    8983,
    9000,
    9001,
    9043,
    9060,
    9080,
    9090,
    9091,
    9200,
    9443,
    9502,
    9800,
    9981,
    10000,
    10250,
    11371,
    12443,
    15672,
    16080,
    17778,
    18091,
    18092,
    20720,
    32000,
    55440,
    55672]

###############################################################################
# WHOIS DEFINITIONS
# IGNORE_WHOIS_RELATED_KEYWORD: To ignore and disable finding generic related domains
###############################################################################

IGNORE_WHOIS_RELATED_KEYWORD = [
    'Registration Private',
    'Domains By Proxy Llc',
    'Redacted For Privacy',
    'Digital Privacy Corporation',
    'Private Registrant',
    'Domain Administrator',
    'Administrator',
]
