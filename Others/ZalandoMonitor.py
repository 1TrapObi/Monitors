# No restocks, only releases
from random_user_agent.params import SoftwareName, HardwareType
from random_user_agent.user_agent import UserAgent

from fp.fp import FreeProxy

from bs4 import BeautifulSoup
import requests
import urllib3

from datetime import datetime
import time

import json
import logging
import dotenv

logging.basicConfig(filename='Zalandolog.log', filemode='a', format='%(asctime)s - %(name)s - %(message)s',
                    level=logging.DEBUG)

software_names = [SoftwareName.CHROME.value]
hardware_type = [HardwareType.MOBILE__PHONE]
user_agent_rotator = UserAgent(software_names=software_names, hardware_type=hardware_type)
CONFIG = dotenv.dotenv_values()

proxyObject = FreeProxy(country_id=[CONFIG['LOCATION']], rand=True)

INSTOCK = []


def scrape_main_site(headers, proxy):
    """
    Scrape the Zalando site and adds each item to an array
    """
    items = []

    # Makes request to site
    url = 'https://m.zalando.co.uk/mens-shoes-trainers/?order=activation_date'
    s = requests.Session()
    html = s.get(url=url, headers=headers, proxies=proxy, verify=False, timeout=15)
    soup = BeautifulSoup(html.text, 'html.parser')
    products = json.loads(str(soup.find('script', {'id': 'z-nvg-cognac-props'}))[65:-12])

    # Stores particular details in array 
    for product in products['articles']:
        item = [
            product['name'],
            product['sku'],
            product['price']['original'],
            product['url_key'],
            product['media'][0]['path']
            ]
        items.append(item)
    
    logging.info(msg='Successfully scraped site')
    s.close()
    return items


def test_webhook():
    """
    Sends a test Discord webhook notification
    """
    data = {
        "username": CONFIG['USERNAME'],
        "avatar_url": CONFIG['AVATAR_URL'],
        "embeds": [{
            "title": "Testing Webhook",
            "description": "This is just a quick test to ensure the webhook works. Thanks again for using these monitors!",
            "color": int(CONFIG['COLOUR']),
            "footer": {'text': 'Made by Yasser'},
            "timestamp": str(datetime.utcnow())
        }]
    }

    result = requests.post(CONFIG['WEBHOOK'], data=json.dumps(data), headers={"Content-Type": "application/json"})

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err)
        logging.error(msg=err)
    else:
        print("Payload delivered successfully, code {}.".format(result.status_code))
        logging.info("Payload delivered successfully, code {}.".format(result.status_code))


def discord_webhook(title, url, thumbnail, price, sku):
    """
    Sends a Discord webhook notification to the specified webhook URL
    """
    data = {
        "username": CONFIG['USERNAME'],
        "avatar_url": CONFIG['AVATAR_URL'],
        "embeds": [{
            "title": title,
            "url": f'https://m.zalando.co.uk{url}.html',
            "thumbnail": {"url": f'https://img01.ztat.net/article/{thumbnail}'},
            "color": int(CONFIG['COLOUR']),
            "footer": {"text": "Made by Yasser"},
            "timestamp": str(datetime.utcnow()),
            "fields": [
                {"name": "Price", "value": price},
                {"name": "SKU", "value": sku}
            ]

        }]
    }

    result = requests.post(CONFIG['WEBHOOK'], data=json.dumps(data), headers={"Content-Type": "application/json"})

    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err)
        logging.error(msg=err)
    else:
        print("Payload delivered successfully, code {}.".format(result.status_code))
        logging.info("Payload delivered successfully, code {}.".format(result.status_code))


def checker(item):
    """
    Determines whether the product status has changed
    """
    return item in INSTOCK


def remove_duplicates(mylist):
    """
    Removes duplicate values from a list
    """
    return [list(t) for t in set(tuple(element) for element in mylist)]


def comparitor(item, start):
    if not checker(item):
        # If product is available but not stored - sends notification and stores
        INSTOCK.append(item)
        if start == 0:
            discord_webhook(
                title=item[0],
                sku=item[1],
                price=item[2],
                url=item[3],
                thumbnail=item[4]
            )


def monitor():
    """
    Initiates monitor
    """
    print('STARTING MONITOR')
    logging.info(msg='Successfully started monitor')

    # Tests webhook URL
    test_webhook()

    # Ensures that first scrape does not notify all products
    start = 1

    # Initialising proxy and headers
    proxy_no = 0
    proxy_list = CONFIG['PROXY'].split('%')
    proxy = {"http": proxyObject.get()} if proxy_list[0] == "" else {"http": f"http://{proxy_list[proxy_no]}"}
    headers = {
        'User-Agent': user_agent_rotator.get_random_user_agent(),
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8'}
    
    # Collecting all keywords (if any)
    keywords = CONFIG['KEYWORDS'].split('%')
    while True:
        try:
            # Makes request to site and stores products 
            items = remove_duplicates(scrape_main_site(headers, proxy))
            for item in items:

                if keywords == '':
                    # If no keywords set, checks whether item status has changed
                    comparitor(item, start)

                else:
                    # For each keyword, checks whether particular item status has changed
                    for key in keywords:
                        if key.lower() in item[0].lower():
                            comparitor(item, start)

            # Allows changes to be notified
            start = 0

            # User set delay
            time.sleep(float(CONFIG['DELAY']))
            
        except Exception as e:
            print(f"Exception found '{e}' - Rotating proxy and user-agent")
            logging.error(e)

            # Rotates headers
            headers = {
                'User-Agent': user_agent_rotator.get_random_user_agent(),
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-encoding': 'gzip, deflate, br',
                'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8'}
            
            if CONFIG['PROXY'] == "":
                # If no optional proxy set, rotates free proxy
                proxy = {"http": proxyObject.get()}

            else:
                # If optional proxy set, rotates if there are multiple proxies
                proxy_no = 0 if proxy_no == (len(proxy_list) - 1) else proxy_no + 1
                proxy = {"http": f"http://{proxy_list[proxy_no]}"}


if __name__ == '__main__':
    urllib3.disable_warnings()
    monitor()
