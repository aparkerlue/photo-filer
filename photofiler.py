# -*- coding: utf-8 -*-

import argparse
import os
import sys
import shutil
from collections import defaultdict
from datetime import datetime
from PIL import Image
from geopy.geocoders import Nominatim

from get_lat_lon_exif_pil import get_exif_data, get_lat_lon


def get_location(exif_data):
    lat_lon = get_lat_lon(exif_data)
    geolocator = Nominatim()
    location = geolocator.reverse(', '.join(str(d) for d in lat_lon))
    return location


def get_datetime(exif_data):
    dtstr = exif_data['DateTimeOriginal']
    dt = datetime.strptime(dtstr, '%Y:%m:%d %H:%M:%S')
    return dt


def get_location_symbol(exif_data):
    try:
        location = get_location(exif_data)
    except Exception:
        return 'NA'

    raw_address = location.raw['address']
    if 'footway' in raw_address:
        locsym = raw_address['footway']
    elif 'path' in raw_address:
        locsym = raw_address['path']
    elif 'neighbourhood' in raw_address:
        locsym = raw_address['neighbourhood']
    elif 'hamlet' in raw_address:
        locsym = raw_address['hamlet']
    elif 'village' in raw_address:
        locsym = raw_address['village']
    elif 'town' in raw_address:
        locsym = raw_address['town']
    elif 'city' in raw_address:
        locsym = raw_address['city']
    elif 'county' in raw_address:
        locsym = raw_address['county']
    elif 'state' in raw_address:
        locsym = raw_address['state']
    elif 'country' in raw_address:
        locsym = raw_address['country']
    else:
        locsym = 'NA'
    return locsym


parser = argparse.ArgumentParser(
    description='Organize photos by date taken'
)
parser.add_argument('files', metavar='FILE', nargs='+',
                    help='''
Image file to organize. If directory, only children are read
                    '''.strip())
args = parser.parse_args()

metainfo = {}
geolocator = Nominatim()
files = []
for f in args.files:
    if os.path.isfile(f):
        files.append(f)
    elif os.path.isdir(f):
        # Include just the direct children of the directory. Including
        # all of the descendants could result in name collisions.
        #
        # Providing multiple directories could also lead to name
        # collisions, but we want to allow at least one directory in
        # order to use this script on a Windows command line.
        for g in os.listdir(f):
            g_path = os.path.join(f, g)
            if os.path.isfile(g_path):
                files.append(g_path)
    else:
        print('warning: skipping {}'.format(f), file=sys.stderr)
for f in files:
    try:
        img = Image.open(f)
    except OSError as err:
        print('warning: {}: {}'.format(f, err), file=sys.stderr)
        continue

    try:
        exif_data = get_exif_data(img)
    except AttributeError as err:
        print('warning: {}: {}'.format(f, err), file=sys.stderr)
        continue

    try:
        dt = get_datetime(exif_data)
    except KeyError as err:
        print('warning: {}: KeyError `{}\''.format(f, err), file=sys.stderr)
        continue
    locsym = get_location_symbol(exif_data)
    metainfo[f] = {
        'dt': dt,
        'loc': locsym,
    }

last_k = None
last_dt = None
last_loc = None
imgdirs = defaultdict(list)
for f in sorted(
        metainfo,
        key=lambda x: '{} {}'.format(metainfo[x]['dt'], os.path.basename(x))
):
    dt = metainfo[f]['dt']
    loc = metainfo[f]['loc']
    if (last_k is not None and last_dt is not None and last_loc is not None
            and loc == last_loc
            and (dt - last_dt).total_seconds() / 60 < 45):
        k = last_k
    else:
        dtstr = dt.strftime('%Y-%m-%d %H.%M')
        k = '{} {}'.format(dtstr, loc)
    imgdirs[k].append(os.path.basename(f))
    last_loc = loc
    last_dt = dt
    last_k = k

print('Proposed directory structure:')
for d in sorted(imgdirs):
    print(d)
    for f in sorted(imgdirs[d]):
        print('  - {}'.format(f))
print()

do_organize = input('Create directories and organize files? (y/[n])? ')
if do_organize != 'y':
    sys.exit()

for d in sorted(imgdirs):
    if os.path.exists(d):
        print('error: {} already exists!'.format(d))
        sys.exit(1)

for d in sorted(imgdirs):
    if os.path.exists(d):
        print('error: {} already exists!'.format(d))
        sys.exit(1)
    os.mkdir(d)
    for f in sorted(imgdirs[d]):
        try:
            shutil.move(f, d)
        except PermissionError as err:
            print('error: Can\'t move {} to {}: {}'.format(f, d, err))

sys.exit()
