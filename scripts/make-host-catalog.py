#!/usr/local/bin/python3.5

import json
import re
import os
import math
import codecs
import urllib
import requests
import ads
import gzip
import statistics
import time
from html import unescape
from glob import glob
from tqdm import tqdm
from collections import OrderedDict
from astropy.coordinates import SkyCoord as coord
from astropy import units as un
from astropy.time import Time as astrotime
from copy import deepcopy
from math import sqrt
from digits import *

hosts = OrderedDict()

def get_event_filename(name):
    return(name.replace('/', '_'))

def uniq_l(values):
    return list(OrderedDict.fromkeys(values).keys())

with open('rep-folders.txt', 'r') as f:
    repfolders = f.read().splitlines()

files = []
for rep in repfolders:
    files += glob('../' + rep + "/*.json") + glob('../' + rep + "/*.json.gz")

for fcnt, eventfile in enumerate(tqdm(sorted(files, key=lambda s: s.lower()))):
    #if fcnt > 100:
    #    break
    fileeventname = os.path.splitext(os.path.basename(eventfile))[0].replace('.json','')

    if not os.path.isfile(eventfile):
        continue

    if eventfile.split('.')[-1] == 'gz':
        with gzip.open(eventfile, 'rt') as f:
            filetext = f.read()
    else:
        with open(eventfile, 'r') as f:
            filetext = f.read()

    item = json.loads(filetext, object_pairs_hook=OrderedDict)
    item = item[list(item.keys())[0]]

    if 'host' in item:
        hn = ''
        hns = [x['value'] for x in item['host']]
        for ho in hosts:
            if len(list(set(hns).intersection(hosts[ho]['host']))):
                hn = hosts[ho]['host'][0]
                hosts[hn]['host'] = uniq_l(hosts[ho]['host'] + hns)
                break
        if not hn:
            hn = hns[0]
            #tqdm.write(hn)

            hosts[hn] = OrderedDict([('host', hns), ('events', []), ('eventdates', []),
                ('types', []), ('photocount', 0), ('spectracount', 0)])

        hosts[hn]['events'].append(item['name'])

        if 'discoverdate' in item and item['discoverdate']:
            datestr = item['discoverdate'][0]['value'].replace('/', '-')
            if datestr.count('-') == 1:
                datestr += '-01'
            elif datestr.count('-') == 0:
                datestr += '-01-01'
            try:
                hosts[hn]['eventdates'].append(astrotime(datestr, format = 'isot').unix)
            except:
                hosts[hn]['eventdates'].append(float("inf"))
        else:
            hosts[hn]['eventdates'].append(float("inf"))

        if 'claimedtype' in item:
            cts = []
            for ct in item['claimedtype']:
                sct = ct['value'].strip('?')
                if sct:
                    cts.append(sct)
            hosts[hn]['types'] = list(set(hosts[hn]['types']).union(cts))

        if 'photometry' in item:
            hosts[hn]['photocount'] += len(item['photometry'])

        if 'spectra' in item:
            hosts[hn]['spectracount'] += len(item['spectra'])

curtime = time.time()
centrate = 1.0/(100.0*365.25*24.0*60.0*60.0)

for hn in hosts:
    finitedates = sorted([x for x in hosts[hn]['eventdates'] if x != float("inf")] + [curtime])
    datediffs = [(finitedates[i+1] - x)*centrate for i, x in enumerate(finitedates[:-1])]
    if len(datediffs) >= 2:
        hosts[hn]['rate'] = (pretty_num(1.0/statistics.mean(datediffs)) + ',' +
            pretty_num(1.0/(statistics.mean(datediffs)*sqrt(float(len(datediffs))))))
    else:
        hosts[hn]['rate'] = ''
    hosts[hn]['events'] = [x for (y,x) in sorted(zip(hosts[hn]['eventdates'], hosts[hn]['events']))]
    del(hosts[hn]['eventdates'])

# Convert to array since that's what datatables expects
hosts = list(hosts.values())
jsonstring = json.dumps(hosts, indent='\t', separators=(',', ':'), ensure_ascii=False)
with open('../hosts.json', 'w') as f:
    f.write(jsonstring)
