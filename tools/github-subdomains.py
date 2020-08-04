#!/usr/bin/python3

# I don't believe in license.
# You can do whatever you want with this program.

import os
import sys
import re
import time
import requests
import random
import argparse
from functools import partial
from colored import fg, bg, attr
from multiprocessing.dummy import Pool


TOKENS_FILE = os.path.dirname(os.path.realpath(__file__))+'/.tokens'


def githubApiSearchCode( token, search, page, sort, order ):
    headers = { "Authorization":"token "+token }
    url = 'https://api.github.com/search/code?per_page=100&s=' + sort + '&type=Code&o=' + order + '&q=' + search + '&page=' + str(page)
    # print(">>> "+url)

    try:
        r = requests.get( url, headers=headers, timeout=5 )
        json = r.json()
        return json
    except Exception as e:
        print( "%s[-] error occurred: %s%s" % (fg('red'),e,attr(0)) )
        return False


def getRawUrl( result ):
    raw_url = result['html_url'];
    raw_url = raw_url.replace( 'https://github.com/', 'https://raw.githubusercontent.com/' )
    raw_url = raw_url.replace( '/blob/', '/' )
    return raw_url;


def readCode( domain_regexp, source, result ):

    time.sleep( random.random() )

    url = getRawUrl( result )
    # print(url)
    if url in t_history_urls:
        return

    output = ''
    t_history_urls.append( url )
    code = doGetCode( url )
    t_local_history = []
    # sys.stdout.write( ">>> calling %s\n" % url )

    if code:
        matches = re.findall( domain_regexp, code, re.IGNORECASE )
        if matches:
            for sub in  matches:
                sub = sub[0].replace('2F','').lower().strip()
                if len(sub) and not sub in t_local_history:
                    t_local_history.append(sub)
                    if source:
                        if not len(output):
                            output = output + ("%s>>> %s%s\n\n" % (fg('yellow'),result['html_url'],attr(0)) )
                        t_history.append( sub )
                        output = output + ("%s\n" % sub)
                    elif not sub in t_history:
                        t_history.append( sub )
                        output = output + ("%s\n" % sub)

    if len(output.strip()):
        sys.stdout.write( "%s\n" % output.strip() )


def doGetCode( url ):
    # print( url )
    try:
        r = requests.get( url, timeout=5 )
    except Exception as e:
        sys.stdout.write( "%s[-] error occurred: %s%s\n" % (fg('red'),e,attr(0)) )
        return False

    return r.text


parser = argparse.ArgumentParser()
parser.add_argument( "-t","--token",help="your github token (required)" )
parser.add_argument( "-d","--domain",help="domain you are looking for (required)" )
parser.add_argument( "-e","--extend",help="also look for <dummy>example.com", action="store_true" )
parser.add_argument( "-s","--source",help="display first url where subdomains are found", action="store_true" )
parser.add_argument( "-v","--verbose",help="verbose mode, for debugging purpose", action="store_true" )
parser.parse_args()
args = parser.parse_args()

t_tokens = []
if args.token:
    t_tokens = args.token.split(',')
else:
    if os.path.isfile(TOKENS_FILE):
        fp = open(TOKENS_FILE,'r')
        t_tokens = fp.read().split("\n")
        fp.close()

if not len(t_tokens):
    parser.error( 'auth token is missing' )

if args.source:
    _source = True
else:
    _source = False

if args.domain:
    _domain = args.domain
else:
    parser.error( 'domain is missing' )

t_sort_order = [
    { 'sort':'indexed', 'order':'desc',  },
    { 'sort':'indexed', 'order':'asc',  },
    { 'sort':'', 'order':'desc',  }
]

t_history = []
t_history_urls = []
_search = '"' + _domain + '"'

### this is a test, looks like we got more result that way
import tldextract
t_host_parse = tldextract.extract( _domain )

if args.extend:
    # which one is
    _search = '"' + t_host_parse.domain + '"'
else:
    # the most effective ?
    _search = '"' + t_host_parse.domain + '.' + t_host_parse.suffix + '"'

_search = _search.replace('-','%2D')
# or simply
# _search = '"' + _domain + '"'
# print( t_host_parse )
# exit()
###

# egrep -io "[0-9a-z_\-\.]+\.([0-9a-z_\-]+)?`echo $h|awk -F '.' '{print $(NF-1)}'`([0-9a-z_\-\.]+)?\.[a-z]{1,5}"


if args.extend:
    # domain_regexp = r'[0-9a-zA-Z_\-\.]+' + _domain.replace('.','\.')
    domain_regexp = r'([0-9a-z_\-\.]+\.([0-9a-z_\-]+)?'+t_host_parse.domain+'([0-9a-z_\-\.]+)?\.[a-z]{1,5})'
else:
    domain_regexp = r'(([0-9a-z_\-\.]+)\.' + _domain.replace('.','\.')+')'

if args.verbose:
    print( "Search: %s" % _search )
    print( "Regexp: %s" % domain_regexp)

for so in t_sort_order:

    page = 1

    if args.verbose:
        print( '\n----- %s %s\n' % (so['sort'],so['order']) )

    while True:

        if args.verbose:
            print("page %d" % page)

        # time.sleep( random.random() )
        token = random.choice( t_tokens )
        t_json = githubApiSearchCode( token, _search, page, so['sort'], so['order'] )

        if not t_json or 'documentation_url' in t_json or 'message' in t_json:
            if args.verbose:
                print(t_json)
            t_tokens.remove(token)
            if len(t_tokens) == 0:
                exit()
            continue

        page = page + 1

        if 'items' in t_json and len(t_json['items']):
            # print('page: %d , %d results' % (page,len(t_json['items'])) )
            # continue
            pool = Pool( 30 )
            pool.map( partial(readCode,domain_regexp,_source), t_json['items'] )
            pool.close()
            pool.join()
        else:
            break

