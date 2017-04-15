from django.conf import settings

import json

from django.conf import settings

SABRE_CONFIGS = getattr(settings, 'SABRE', None)

sabre_endpoints = {
    # base url
    'base_test': 'https://api.test.sabre.com',
    'base_prod': 'https://api.sabre.com',               
    
    # Air Search
    'instaflights': '/v1/shop/flights',
    'flights_to': '/v1/shop/flights/cheapest/fares',
    'seat_map': '/v3.0.0/book/flights/seatmaps?mode=seatmaps',
    'lead_price': '/v2/shop/flights/fares',
    'destination_finder': '/v2/shop/flights/fares',
    'geo_code': '/v1/lists/utilities/geocode/locations',
    'tagid': '/v1/shop/flights/tags/',

    # Air Intelligence
    'top_destinations': '/v1/lists/top/destinations',

    # Air Utility
    'alliance_lookup': '/v1/lists/utilities/airlines/alliances/',
    'equipment_lookup': '/v1/lists/utilities/aircraft/equipment/',
    'multi_city_airport_lookup': '/v1/lists/supported/cities',
    'countries_lookup': '/v1/lists/supported/countries',
    'city_pairs_shop_lookup': '/v1/lists/supported/shop/flights/origins-destinations',
    'city_pairs_historical_lookup': '/v1/lists/supported/historical/flights/origins-destinations',
    'city_pairs_forecast_lookup': '/v1/lists/supported/forecast/flights/origins-destinations',
    'travel_theme_lookup': 'UNIMPLEMENTED',
    'airports_at_cities_lookup': 'UNIMPLEMENTED',
    
    # Hotel
    'get_hotel_list': '/v1.0.0/shop/hotels',
    'get_hotel_content': '/v1.0.0/shop/hotels/content?mode=content',
    'get_hotel_image': '/v1.0.0/shop/hotels/image?mode=image',
    'Geg_hotel_media': '/v1.0.0/shop/hotels/media',
    
    # Cars 
    'car_availability': '/v2.4.0/shop/cars',
    
    # utility
    'geo_autocomplete': '/v1/lists/utilities/geoservices/autocomplete/',
    'geocode': {
        'method': 'POST',
        'url': '/v1/lists/utilities/geocode/locations/',
        'object': json.dumps( { "GeoCodeRQ": { "PlaceById":{ "Id":"DFW", "BrowseCategory": { "name": "AIR" } } }})
    },
    'airline_lookup': {
        'method': 'GET',
        'url': '/v1/lists/utilities/airlines/'
    }
}

DEBUG = getattr(settings, 'DEBUG')
sabre_endpoints['base'] = sabre_endpoints['base_test'] if DEBUG and SABRE_CONFIGS['TEST'] else sabre_endpoints['base_prod']

# other configs
configurations = {

}

# django ? get from environment
configurations.update(SABRE_CONFIGS)


''' :TODO  for platforms other than django import configs here.. '''