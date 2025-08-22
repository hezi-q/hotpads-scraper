import csv
from concurrent.futures import ThreadPoolExecutor
import json
import requests
from threading import Lock

from bs4 import BeautifulSoup
import pandas as pd


lock = Lock()


SCRAPER_API_KEY = '<YOUR_SCRAPER_API_KEY>'  # Get your free API key from https://www.scraperapi.com/


def get_params(zipcode):
    print(zipcode)
    headers = {
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    }

    params = {
        'resourceId': zipcode,
    }

    response = requests.get(
        'https://hotpads.com/hotpads-api/api/v2/area/byResourceId',
        params=params,
        headers=headers,
    )
    raw_coordinates = response.json()['data']

    params = {
        'orderBy': 'score',
        'bedrooms': '0,1,2,3,4,5,6,7,8plus',
        'bathrooms': '0,0.5,1,1.5,2,2.5,3,3.5,4,4.5,5,5.5,6,6.5,7,7.5,8plus',
        'pets': '',
        'laundry': '',
        'amenities': '',
        'propertyTypes': 'condo,divided,garden,house,land,large,medium,townhouse',
        'listingTypes': 'rental,room,sublet,corporate',
        'keywords': '',
        'includePhotosCollection': 'true',
        'visible': 'favorite,inquiry,new,note,notified,viewed',
        'areas': '1225390162',
        'lat': f"{raw_coordinates['coordinates']['lat']}",
        'lon': f"{raw_coordinates['coordinates']['lat']}",
        'maxLat': f"{raw_coordinates['maxLat']}",
        'maxLon': f"{raw_coordinates['maxLon']}",
        'minLat': f"{raw_coordinates['minLat']}",
        'minLon': f"{raw_coordinates['minLon']}",
        'offset': '0',
        'channels': '',
        'components': 'basic,useritem,quality,model,photos',
        'trimResponse': 'true',
    }

    return params


def get(url):
    response = requests.get(f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={url}")
    return BeautifulSoup(response.text, 'html.parser')


def parse_properties(raw_properties, writer):
    raw_properties = raw_properties['listings']['listingGroups']['byCoords']

    for raw_property in raw_properties:
        _property = {}

        _property['url'] = 'https://hotpads.com' + raw_property['uriMalone']
        if raw_property.get('address'):
            address = raw_property['address']
            _property['street'] = address['street']
            _property['city'] = address['city']
            _property['state'] = address['state']
            _property['zip'] = address['zip']

        if raw_property.get('listingMinMaxPriceBeds'):
            features = raw_property['listingMinMaxPriceBeds']
            _property['beds'] = features.get('maxBeds', '')
            _property['baths'] = features.get('maxBaths', '')
            _property['min_price'] = features.get('minPrice', '')
            _property['max_price'] = features.get('maxPrice', '')
            _property['min_sqft'] = features.get('minSqft', '')
            _property['max_sqft'] = features.get('maxSqft', '')

        _property['listing_type'] = raw_property.get('listingType', '')
        _property['description'] = raw_property.get('fullDescription', '')

        if raw_property.get('amenities'):
            _property['amenities'] = '\n'.join(set(raw_property['amenities'].get('amenities', [])))
            
            if raw_property['amenities'].get('petPolicies'):
                _property['pet_policies'] = '\n'.join(set([p['petType'] for p in raw_property['amenities'].get('petPolicies', []) if p['allowed']]))

        with lock:
            print(_property)
            writer.writerow(_property)


def crawl_properties(zipcode, writer, page=1):
    print(f'zipcode = {zipcode}, page = {page}')
    url = f'https://hotpads.com/{zipcode}/apartments-for-rent?page={page}'
    soup = get(url)

    raw_properties = soup.select_one('script:-soup-contains("__PRELOADED_STATE__")').get_text(strip=True).split('window.__PRELOADED_STATE__ =')[1]
    raw_properties = json.loads(raw_properties)
    
    if len(soup.select('.PagerContainer-page-number')) < page: return

    parse_properties(raw_properties, writer)

    if soup.select('.PagerItem:-soup-contains("Next")'):
        crawl_properties(zipcode, writer, page+1)


def main():
    zipcodes = ['10001', '10002', '10003', '10004', '10005', '10006', '10007', '10009', '10010', '10011', '10012', '10013', '10014', '10016', '10017', '10018', '10019', '10020', '10021', '10022', '10023', '10024', '10025', '10026', '10027', '10028', '10029', '10030', '10031', '10032', '10033', '10034', '10035', '10036', '10037', '10038', '10039', '10040',]


    with open('hotpads.csv', 'w', newline='', encoding='utf-8') as f2:
        writer = csv.DictWriter(f2, fieldnames=[
            'url',
            'street',
            'city',
            'state',
            'zip',
            'beds',
            'baths',
            'min_price',
            'max_price',
            'min_sqft',
            'max_sqft',
            'listing_type',
            'description',
            'amenities',
            'pet_policies'
        ])

        writer.writeheader()

        with ThreadPoolExecutor(max_workers=20) as executor:
            for row in zipcodes:
                executor.submit(crawl_properties, row[0], writer)
    
    pd.read_csv('hotpads.csv').drop_duplicates().to_csv('hotpads.csv', index=False)


if __name__ == '__main__':
    main()
