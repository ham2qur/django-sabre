import base64
import collections
import datetime
import gzip
import json
import os
import re
from xml.etree import ElementTree

from django.conf import settings
from django.core.cache import cache
from django.template.loader import render_to_string
import requests
from suds.client import Client

from sabre import xmltodict
from sabre.sabre_dev_studio import sabre_configs
from sabre.sabre_dev_studio import sabre_configs as config
from sabre.sabre_dev_studio import sabre_utils, sabre_exceptions, session
from sabre.sabre_dev_studio.sabre_configs import sabre_endpoints
from sabre.sabre_dev_studio.sabre_exceptions import UnsupportedMethodError, \
    SabreErrorBadRequest
from sabre.sabre_dev_studio.sabre_utils import country_code_lookup


# from google.appengine.api import urlfetch
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
    

# from google.appengine.api import memcache
PREFIX_SESSION = "session_"
MAX_SESSIONS=1




# Local imports
class SabreDevStudio(object):
    def __init__(self, environment='test', return_obj=True):
        self.auth_headers = None

        self.client_id = None
        self.client_secret = None
        self.token = None
        self.token_expiry = None

        self.return_obj = return_obj

        if environment is 'test':
            self.host = sabre_endpoints['base_test']
#             self.host = 'https://api-crt.cert.havail.sabre.com'
        elif environment is 'prod':
            self.host = sabre_endpoints['base_prod']
        else: # default to test
            self.host = sabre_endpoints['base_test']
#             self.host = 'https://api-crt.cert.havail.sabre.com'

    # init_with_config
    # () -> ()
    # Initializes the class with an ID and secret from a config file
    # Useful for testing and interactive mode
    def init_with_config(self, config_file='config.json'):
        raw_data = open(config_file).read()

        data = json.loads(raw_data)

        client_secret = data['sabre_client_secret']
        client_id = data['sabre_client_id']

        self.set_credentials(client_id, client_secret)
        self.authenticate()

    # make_endpoint
    # String -> String
    # Converts a relative endpoint to an absolute URI
    def make_endpoint(self, endpoint):
        return self.host + endpoint

    # set_credentials
    # String -> String -> ()
    # Sets the Sabre Dev Studio Client ID and Secret to the instance
    # Must be done before token is requested
    def set_credentials(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret 

    # authenticate
    # () -> ()
    # This method uses the client ID and client secret provided in set_credentials
    # to request the token from Sabre. The token is then saved in the internal state
    # of the instance in self.token
    def authenticate(self):
        if not self.client_id or not self.client_secret:
            raise sabre_exceptions.NoCredentialsProvided

        token_resp = self.get_token_data(self.client_id, self.client_secret)
        self.verify_response(token_resp)

        token_json = token_resp.json()
        
        self.token = token_json.get('access_token')
        self.token_expiry = datetime.datetime.now() + datetime.timedelta(0, token_json.get('expires_in'))

    def stringToBase64(self, s):
        return base64.b64encode(s.encode('utf-8'))


    # Sabre Authentication Sample 
    # https://developer.sabre.com/docs/read/rest_basics/authentication#authenticatedReqAndRespFormats
    def get_token_data(self, client_id, client_secret):

        # step 1: Construct your Client ID
        b64_client_id = self.stringToBase64(client_id)
        b64_client_secret = self.stringToBase64(client_secret)
        
        # step 2: Base64 encode your credentials
        encoded = str(b64_client_id) + ':' + str(b64_client_secret)
        print(encoded)
        encoded = self.stringToBase64(encoded)
        print(encoded)

        encoded = 'VmpFNmJXUXpielZ6ZG00NWRHTnVPR3hsZGpwRVJWWkRSVTVVUlZJNlJWaFU6VkZKdU5URmhWMmM9'
        headers = {
            'Authorization' : 'Basic ' + encoded,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        payload = {
            'grant_type': 'client_credentials'
        }
        
        # Step 3: Get an access token
        data = requests.post(self.make_endpoint('/v2/auth/token/'),
                             headers=headers,
                             data=payload)

        return data

    # request
    # String -> String -> Dictionary? -> Dictionary? -> (ResponseData or dict)
    # The generic request function -- all API requests go through here
    # Should be called by a higher-level wrapper like instaflights(...)
    #    method is a String, 'GET', 'PUT', 'PATCH', 'POST', or 'DELETE'
    #    endpoint is a relative endpoint
    #    payload is the data -- added as query params for GET
    # Returns an object with the properties of the response data
    def request(self, method, endpoint, payload=None, additional_headers=None):
        now = datetime.datetime.now()

        # Check for token
        if not self.token:
            raise sabre_exceptions.NotAuthorizedError

        if not self.token_expiry:
            pass
        elif self.token_expiry < now:
            # Authenticate again
            self.authenticate()

        endpoint = self.make_endpoint(endpoint)
        auth_header = {
            'Authorization': 'Bearer ' + self.token
        }

        headers = additional_headers.copy() if additional_headers else {}
        headers.update(auth_header)

        if method == 'GET':
            resp = requests.get(endpoint, headers=headers, params=payload)
        elif method == 'PUT':
            resp = requests.put(endpoint, headers=headers, data=payload)
        elif method == 'PATCH':
            resp = requests.put(endpoint, headers=headers, data=payload)
        elif method == 'POST':
            resp = requests.post(endpoint, headers=headers, data=payload)
        elif method == 'DELETE':
            resp = requests.delete(endpoint, headers=headers)
        else:
            raise UnsupportedMethodError

        self.verify_response(resp)

#         if self.return_obj:
#             resp_data = self.process_response(resp.json())
#         else:
#             resp_data = resp.json()
        resp_data = resp.json()
        return resp_data

    # verify_response
    # Response -> ()
    # Checks the status code of a response and raises the appropriate exception
    # if the status code is invalid (not in the 2xx range)
    def verify_response(self, resp):
        if resp.status_code >= 200 and resp.status_code < 299:
            pass

        else:
            if resp.status_code == 400:
                raise sabre_exceptions.SabreErrorBadRequest(resp.json())
            elif resp.status_code == 401:
                raise sabre_exceptions.SabreErrorUnauthenticated(resp.json())
            elif resp.status_code == 403:
                raise sabre_exceptions.SabreErrorForbidden(resp.json())
            elif resp.status_code == 404:
                raise sabre_exceptions.SabreErrorNotFound(resp.json())
            elif resp.status_code == 405:
                raise sabre_exceptions.SabreErrorMethodNotAllowed()
            elif resp.status_code == 406:
                raise sabre_exceptions.SabreErrorNotAcceptable(resp.json())
            elif resp.status_code == 429:
                raise sabre_exceptions.SabreErrorRateLimited(resp.json())

            elif resp.status_code == 500:
                print(resp.text)
                raise sabre_exceptions.SabreInternalServerError(resp.text)
            elif resp.status_code == 503:
                raise sabre_exceptions.SabreErrorServiceUnavailable
            elif resp.status_code == 504:
                raise sabre_exceptions.SabreErrorGatewayTimeout

    # process_response
    # JSON Dictionary -> ResponseData
    # Converts a dictionary into a python object with Pythonic names
    def process_response(self, json_obj):
        sabre_utils.convert_keys(json_obj)

        json_str = json.dumps(json_obj)
        obj = json.loads(json_str,
                         object_hook=lambda d: collections.namedtuple('ResponseData', d.keys())(*d.values()))

        return obj
    
    # SOAP APIs Handler
    #
    #
    def get_service(self, params=None):
        """
            Initializes all session poll sessions.
        """
        params.update(sabre_configs.configurations)
        tpl = render_to_string('sabre/xml/' + params["Action"] + '.xml', params)
        print (tpl)
        
        # implementation for memcache
    #     urlfetch.set_default_fetch_deadline(60)
    #     result = urlfetch.fetch(url=config.configurations["URL_WS"],
    #              payload=tpl,
    #              method=urlfetch.POST,
    #              headers={"Content-Type": "text/xml","Accept": "text/xml","Accept-Encoding":"gzip"})
                   #headers={"Content-Type": "text/xml","Accept": "text/xml"})
    
        # implementation for redirect
        result = requests.post(sabre_configs.configurations["WSDL_URL"], 
                               {"Content-Type": "text/xml","Accept": "text/xml","Accept-Encoding":"gzip"}, tpl)
    
        gzip_stream = StringIO.StringIO(result.content)
        gzip_file = gzip.GzipFile(fileobj=gzip_stream)
        ungzipped = gzip_file.read()
        doc = xmltodict.parse(ungzipped,attr_prefix='_')
        return doc#json.dumps(doc)
        ##doc = xmltodict.parse(result.content,attr_prefix='_')
        #return doc    

    # instaflights
    # Dictionary -> ResponseData
    # Executes a request to Sabre's instaflights endpoint with the options specified
    def instaflights(self, options):
        resp = self.request('GET', sabre_endpoints['instaflights'], options)
        return resp
    
    # The Tag ID Lookup endpoint has a required 
    # A TagID is returned with each itinerary when 
    # enabletagging=true used in a previous 
    # InstaFlights Search API request.
    def tagid(self, tag_id):
        resp = self.request('GET', sabre_endpoints['tagid'] + tag_id)
        return resp

    # flights_to
    # String -> String? -> ResponseData
    # Executes a request to Sabre's "Flights To" endpoint with the options specified
    # Returns 20 of the lowest published fares available for a given destination
    # Defaults to 'US' as point of sale
    def flights_to(self, city_code, point_of_sale=None):
        opts = {
            'pointofsalecountry': point_of_sale
        }

        resp = self.request('GET',
                            sabre_endpoints['flights_to'] + '/' + city_code,
                            opts)

        return resp

    # lead_price
    # String -> String -> [Number] -> String? -> Date? -> Number? ->
    #    Number? -> ResponseData 
    # Executes a request to Sabre's "Lead Price" endpoint with the arguments specified
    # Gives the cheapest dates and fare for the specified origin, destination
    # and length of stay
    def lead_price(self, origin, destination, length_of_stay,
                   point_of_sale=None, departure_date=None, min_fare=None, 
                   max_fare=None, other_opts={}):

        opts = other_opts.copy()
        opts['origin'] = origin
        opts['destination'] = destination
        
        if point_of_sale:
            opts['pointofsalecountry'] = point_of_sale
        else:
            # Get point of sale country for origin
            result = country_code_lookup(origin)
            opts['pointofsalecountry'] = result if result else 'US'

        if length_of_stay is not None and isinstance(length_of_stay, list):
            opts['lengthofstay'] = ','.join(map(str, length_of_stay))
        elif length_of_stay is not None:
            opts['lengthofstay'] = length_of_stay

        if departure_date:
            opts['departuredate'] = self.convert_date(departure_date);
        if min_fare:
            opts['minfare'] = min_fare
        if max_fare:
            opts['maxfare'] = max_fare

        resp = self.request('GET',
                            sabre_endpoints['lead_price'],
                            opts)
        
        return resp

    # lead_price_opts
    # Dictionary -> ResponseData 
    # Executes a request to Sabre's "Lead Price" endpoint with the arguments specified
    # Gives the cheapest dates and fare for the specified origin, destination
    # and length of stay
    def lead_price_opts(self, opts):
        resp = self.request('GET',
                            sabre_endpoints['lead_price'],
                            opts)
        
        return resp


    # destination_finder
    # Executes a request to Sabre's "Lead Price" endpoint with the arguments specified
    # Gives the cheapest dates and fare for the specified origin, destination
    # and length of stay
    def destination_finder(self, origin, destination=None, length_of_stay=None,
                           point_of_sale=None,
                           departure_date=None, return_date=None,
                           earliest_departure_date=None, latest_departure_date=None,
                           min_fare=None, max_fare=None,
                           region=None, theme=None, location=None,
                           cost_per_mile=None,
                           other_opts={}):

        opts = other_opts.copy()
        opts['origin'] = origin

        if point_of_sale:
            opts['pointofsalecountry'] = point_of_sale
        else:
            # Get point of sale country for origin
            result = country_code_lookup(origin)
            opts['pointofsalecountry'] = result if result else 'US'

        if destination:
            opts['destination'] = destination

        if length_of_stay is not None and isinstance(length_of_stay, list):
            opts['lengthofstay'] = ','.join(map(str, length_of_stay))
        elif length_of_stay is not None:
            opts['lengthofstay'] = length_of_stay

        if departure_date:
            opts['departuredate'] = self.convert_date(departure_date);
        if return_date:
            opts['returndate'] = self.convert_date(return_date);
        if earliest_departure_date:
            opts['earliestdeparturedate'] = self.convert_date(earliest_departure_date);
        if latest_departure_date:
            opts['latestdeparturedate'] = self.convert_date(latest_departure_date);
        if min_fare:
            opts['minfare'] = min_fare
        if max_fare:
            opts['maxfare'] = max_fare
        if region:
            opts['region'] = region
        if theme:
            opts['theme'] = theme
        if location:
            opts['location'] = location
        if cost_per_mile:
            opts['pricepermile'] = cost_per_mile

        resp = self.request('GET',
                            sabre_endpoints['destination_finder'],
                            opts)
        
        return resp


    # destination_finder_opts
    # Dictionary -> ResponseData 
    # Executes a request to Sabre's "Lead Price" endpoint with the options specified
    # as query parameters
    def destination_finder_opts(self, opts):
        resp = self.request('GET',
                            sabre_endpoints['destination_finder'],
                            opts)
        
        return resp

    # top_destinations
    # String -> String? -> String? -> Int? ->
    #    String? -> String? -> Int? -> ResponseData 
    # Executes a request to Sabre's "Top Destinations" endpoint with the 
    # options specified. Returns most popular destinations based on the params.
    # origin is 2 characters => interpreted as country
    # origin is 3 characters => interpreted as city
    # destinationtype = ['DOMESTIC', 'INTERNATIONAL', 'OVERALL']
    # weeks is the number of weeks to look back for data
    def top_destinations(self, origin, destination_type=None,
                         theme=None, num_results=20, destination_country=None,
                         region=None, weeks=2):

        opts = {}
        if len(origin) == 2:
            opts['origincountry'] = origin
        else:
            opts['origin'] = origin

        if destination_type:
            opts['destinationtype'] = destination_type
        if theme:
            opts['theme'] = theme
        if num_results:
            opts['topdestinations'] = num_results
        if destination_country:
            opts['destinationcountry'] = destination_country
        if region:
            opts['region'] = region
        if weeks:
            opts['lookbackweeks'] = weeks

        resp = self.request('GET',
                            sabre_endpoints['top_destinations'],
                            opts)
        return resp

    # top_destinations_opts
    # Dictionary -> ResponseData 
    # Executes a request to Sabre's "Top Destinations" endpoint with the 
    # options specified as query parameters. 
    def top_destinations_opts(self, opts):
        resp = self.request('GET',
                            sabre_endpoints['top_destinations'],
                            opts)
        
        return resp

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


    # alliance_lookup
    # String -> ResponseData
    # Gets a list of airlines for a given alliance
    def alliance_lookup(self, alliance_code):
        if alliance_code not in ['*A', '*O', '*S']:
            return None
        else:
            resp = self.request('GET',
                                sabre_endpoints['alliance_lookup'],
                                { 'alliancecode': alliance_code })
            return resp

    # equipment_lookup
    # String -> String
    # Returns the aircraft name associated with a specified IATA aircraft equipment code
    def equipment_lookup(self, aircraft_code):
        resp = self.request('GET',
                            sabre_endpoints['equipment_lookup'],
                            { 'aircraftcode': aircraft_code })
        try:
            return resp.aircraft_info[0].aircraft_name
        except:
            return None

    # multi_city_airport_lookup
    # String -> ResponseData
    # Returns the cities in a given country (supplied as a two-letter country code)
    def multi_city_airport_lookup(self, country_code):
        resp = self.request('GET',
                            sabre_endpoints['multi_city_airport_lookup'],
                            { 'country': country_code })
        return resp.cities if resp else None


    # countries_lookup
    # String -> ResponseData
    # Returns the valid origin/destination countries for a given point of sale
    # Origin countries: resp.origin_countries
    # Destination countries: resp.destination_countries
    def countries_lookup(self, point_of_sale='US'):
        resp = self.request('GET',
                            sabre_endpoints['countries_lookup'],
                            { 'pointofsalecountry': point_of_sale })
        return resp

    # city_pairs_lookup
    # String -> String? -> String? -> String? -> String? -> String? -> ResponseData
    # Returns the valid origin/destination city pairs for
    # a given point of sale & country
    def city_pairs_lookup(self, endpoint, point_of_sale=None, origin_country=None,
                          destination_country=None, origin_region=None,
                          destination_region=None):
        if endpoint not in ['shop', 'historical', 'forecast']:
            error_string = "Invalid endpoint %s specified for city pairs lookup" % endpoint
            raise sabre_exceptions.InvalidInputError(error_string)
        else:
            endpoint = 'city_pairs_' + endpoint + '_lookup'

        opts = {
            'pointofsalecountry': point_of_sale,
        }

        if origin_country:
            opts['origincountry'] = origin_country
        if destination_country:
            opts['destinationcountry'] = destination_country
        if origin_region:
            opts['originregion'] = origin_region
        if destination_region:
            opts['destinationregion'] = destination_region

        resp = self.request('GET',
                            sabre_endpoints[endpoint],
                            opts)

        return resp


    # city_pairs_lookup_opts
    # String -> Dictionary -> ResponseData
    # Returns the valid origin/destination city pairs for
    # a given point of sale & country
    def city_pairs_lookup_opts(self, endpoint, opts):
        if endpoint not in ['shop', 'historical', 'forecast']:
            error_string = "Invalid endpoint %s specified for city pairs lookup" % endpoint
            raise sabre_exceptions.InvalidInputError(error_string)
        else:
            endpoint = 'city_pairs_' + endpoint + '_lookup'

        resp = self.request('GET',
                            sabre_endpoints[endpoint],
                            opts)
        return resp
    
    #
    #
    #
    #
    def get_hotel_list(self, options):
        resp = self.request('POST', sabre_endpoints['get_hotel_list'], options)
        return resp
    
    
    
        
    #
    #
    #
    #
    def get_hotel_content(self, options):
        resp = self.request('POST', sabre_endpoints['get_hotel_content'], options)
        return resp
    
    
        
    #
    #
    #
    #
    def get_hotel_image(self, options):
        resp = self.request('POST', sabre_endpoints['get_hotel_image'], options)
        return resp
    
    
    
    #
    #
    #
    #    
    def get_hotel_media(self, options):
        resp = self.request('POST', sabre_endpoints['get_hotel_media'], options)
        return resp
    
    #
    #
    #
    #
    def car_availability(self, options):
        resp = self.request('POST',
                        sabre_endpoints['car_availability'],
                        json.dumps(options, sort_keys=True),
                        additional_headers={'Content-Type': 'application/json'});     
        return resp
#         resp = self.request('POST', sabre_endpoints['car_availability'], options, additional_headers={'Content-Type': 'application/json'})
    
    #
    #
    #
    #    
    def get_vehicle_media(self, options):
        resp = self.request('POST', sabre_endpoints['get_vehicle_media'], options)
        return resp
    
    #
    #
    #
    #
    def geo_autocomplete(self, options):
        resp = self.request('GET', sabre_endpoints['geo_autocomplete'], options)
        return resp
    
    
    # https://developer.sabre.com/docs/read/rest_apis/utility/geo_code/
    # The Geo Code API returns the geographic information of a given location.
    def geocode(self, options):
        additional_headers = {'Content-Type': 'application/json'}
        resp = self.request(sabre_endpoints['geocode']['method'], 
                            sabre_endpoints['geocode']['url'], 
                            json.dumps(options, sort_keys=True), 
                            additional_headers=additional_headers)
        return resp
    
    # https://developer.sabre.com/docs/read/rest_apis/utility/airline_lookup/
    # The Airline Lookup API returns the airline name associated with a specified IATA airline code.
    # Sample value: airlinecode=AC,A2,A9
    def airline_lookup(self, airline_code):
        resp = self.request(sabre_endpoints['airline_lookup']['method'], 
                            sabre_endpoints['airline_lookup']['url'], 
                            { 'airlinecode': airline_code })
        return resp
    
    
    def soap_services(self, template_values, action, service):
        binary_security_token = Session.get_session()
        template_values["BinarySecurityToken"] = binary_security_token
        template_values["Action"] = action
        template_values["Service"] = service
        result = self.get_service(template_values)
        Session.free_session()
        return result

    # 
    #
    #
    def bargain_finder_max_RQ(self, template_values):
        result = self.soap_services(template_values, action='BargainFinderMaxRQ', service='BargainFinderMaxRQ')
        return result
    
    
    # Hotel Availability
    # https://developer.sabre.com/docs/read/soap_apis/hotel/search/hotel_availability
    # Authentication: Session Token
    def hotel_availability(self, template_values):
        result = self.soap_services(template_values, action='OTA_HotelAvailLLSRQ', service='OTA_HotelAvailLLSRQ')
        return result
    
class Session(object):
    
    sabre = SabreDevStudio()
    
    @staticmethod
    def create_session():
        """
            Create a saber session.
        """
        token=None
        session_create_rs = Session.sabre.get_service({
            "Service":"Session",
            "Action":"SessionCreateRQ"
          })
    
        try:
            token=session_create_rs["soap-env:Envelope"]["soap-env:Header"]["wsse:Security"]["wsse:BinarySecurityToken"]["#text"]
        except:
            import sys
            import logging
            logging.info(session_create_rs)
            logging.error(sys.exc_info()[0])
    
        return token
    
    @staticmethod
    def get_session():
        """
            Blocks the session so that it can not be used in the session poll.
        """
        index = cache.decr(key="index_sessions")
        return cache.get(PREFIX_SESSION + str(index))
    
    @staticmethod
    def free_session():
        """
        It frees the session to be used in the session poll.
        """
    #     index = memcache.incr(key="index_sessions")
        index = cache.incr(key="index_sessions")
        return index
    
    @staticmethod
    def close_session(binary_security_token):
        """
            Close session on saber.
        """
        return Session.sabre.get_service({
            "Binary_security_token":binary_security_token,
            "Service":"Session",
            "Action":"SessionCloseRQ"
        })
    
    @staticmethod
    def refresh_session(binary_security_token):
        """
            Refresh a session poll session.
        """
        return Session.sabre.get_service({
            "Binary_security_token":binary_security_token,
            "Service":"OTA_PingRQ",
            "Action":"OTA_PingRQ",
            "TimeStamp": datetime.datetime.now().isoformat()
        })
    
    @staticmethod
    def close_session_pool(max=MAX_SESSIONS):
        """
            Close all sessions on saber.
        """
        import logging
        logging.info("begin >> close_session_pool");
    #     memcache.delete(key="index_sessions")
        cache.delete(key="index_sessions")
        list_sessions = []
        for x in range(0, max):
            list_sessions.append(str(x));
    #     dict_sessions=memcache.get_multi(list_sessions, key_prefix=PREFIX_SESSION)
        dict_sessions = cache.get_many(list_sessions, key_prefix=PREFIX_SESSION)
        for key,value in dict_sessions.iteritems():
            logging.info("key : {0} value: {1} ".format(key,value))
            Session.close_session(binary_security_token=value)
    
        logging.info("end >> close_session_pool");
    #     return memcache.delete_multi(list_sessions,key_prefix=PREFIX_SESSION)
        return cache.delete_many(list_sessions, key_prefix=PREFIX_SESSION)
    
    @staticmethod
    def refresh_session_pool(max=MAX_SESSIONS):
        """
            Refresh all session poll sessions.
        """
        import logging
        logging.info("begin >> refresh_all_sessions");
        list_sessions = []
        for x in range(0, max):
            list_sessions.append(str(x));
        #dict_sessions = memcache.get_multi(list_sessions, key_prefix=PREFIX_SESSION)
        dict_sessions = cache.get_many(list_sessions, key_prefix=PREFIX_SESSION)
        for key,value in dict_sessions.iteritems():
            logging.info("key : {0} value: {1} ".format(key, value))
            Session.refresh_session(binary_security_token=value)
        logging.info("end >> refresh_all_sessions");
        return True
    
    @staticmethod
    def create_session_pool(max=MAX_SESSIONS):
        """
            Initializes all session poll sessions.
        """
        import logging
        logging.info("begin >> create_session_pool")
    #     memcache.delete(key="index_sessions")
        cache.delete(key="index_sessions")
        sessions = {}
        for x in range(0, max):
            token = Session.create_session()
            logging.info("key >> {0} value >> {1} ".format(x,token))
            sessions[str(x)] = token
    #     key_sessions=memcache.set_multi(sessions, key_prefix=PREFIX_SESSION)
        key_sessions=cache.set_many(sessions, key_prefix=PREFIX_SESSION)
    #     memcache.set(key="index_sessions", value=max)
        cache.set(key="index_sessions", value=max)
        logging.info("end >> create_session_pool")
        return key_sessions    
