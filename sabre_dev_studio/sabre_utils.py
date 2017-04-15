import base64
import collections
import datetime
import json
import re

import requests

from sabre.sabre_dev_studio import sabre_endpoints


# Local imports
# convert_date
# datetime -> str
# Converts a Python date object to a Sabre-compatible date string
def convert_date(date):
    return date.strftime('%Y-%m-%d')

# convert_keys
# JSON Dictionary -> ResponseData
# Converts a dictionary into a python object with Pythonic names
def convert_keys(d):
    if isinstance(d, list):
        for elem in d:
            convert_keys(elem)
        return
    elif not isinstance(d, dict):
        return

    for key in d.keys():
        # Pythonize

        # Camelcase to _
        s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', key)
        s = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()

        # Replace non-alphanumeric characters with underscores
        s = re.sub('[^0-9a-zA-Z]+', '_', s)

        # Remove leading numbers
        s = re.sub('^[0-9]', '', s)

        # Replace whitespace with underscore
        s = s.replace(' ', '_')

        # Consolidate duplicate underscores
        s = re.sub('__*', '_', s)

        # Remove trailing underscore
        s = re.sub('_*$', '', s)

        d[s] = d[key]
        if s != key:
            del d[key]

        convert_keys(d[s])

# country_code_lookup
# String -> String?
# Finds a country code given an airport/city code
def country_code_lookup(self, code):
    opts = [{
        "GeoCodeRQ": {
            "PlaceById": {
                "Id": code,
                "BrowseCategory": {
                    "name": "AIR"
                }
            }
        }
    }]

    try:
        resp = self.request('POST',
                            sabre_endpoints['geo_code'],
                            json.dumps(opts, sort_keys=True),
                            additional_headers={'Content-Type': 'application/json'})
        code = resp.results[0].geo_code_rs.place[0].country
        return code
    except:
        return None
