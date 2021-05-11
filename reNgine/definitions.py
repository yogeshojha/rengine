#!/usr/bin/python
import logging

###############################################################################
# TOOLS DEFINITIONS
###############################################################################
logger = logging.getLogger('django')

###############################################################################
# TOOLS DEFINITIONS
###############################################################################

AMASS_COMMAND = '/app/tools/amass enum'
###############################################################################
# YAML CONFIG DEFINITIONS
###############################################################################

SUBDOMAIN_DISCOVERY = 'subdomain_discovery'
PORT_SCAN = 'port_scan'
VISUAL_IDENTIFICATION = 'visual_identification'
DIR_FILE_SEARCH = 'dir_file_search'
FETCH_URL = 'fetch_url'
INTENSITY = 'intensity'

USES_TOOLS = 'uses_tool'
THREAD = 'thread'
AMASS_WORDLIST = 'amass_wordlist'
AMASS_CONFIG = 'amass_config'
SUBFINDER_CONFIG = 'subfinder_config'
NAABU_RATE = 'rate'
PORT = 'port'
PORTS = 'ports'
EXCLUDE_PORTS = 'exclude_ports'
EXTENSIONS = 'extensions'
RECURSIVE = 'recursive'
RECURSIVE_LEVEL = 'recursive_level'
WORDLIST = 'wordlist'
HTTP_TIMEOUT = 'http_timeout'
SCREENSHOT_TIMEOUT = 'screenshot_timeout'
SCAN_TIMEOUT = 'scan_timeout'
EXCLUDED_SUBDOMAINS = 'excluded_subdomains'
IGNORE_FILE_EXTENSION = 'ignore_file_extension'

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
