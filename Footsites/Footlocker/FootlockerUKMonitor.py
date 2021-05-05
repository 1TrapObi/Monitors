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


logging.basicConfig(filename='Footlockerlog.log', filemode='a', format='%(asctime)s - %(name)s - %(message)s', level=logging.DEBUG)

software_names = [SoftwareName.CHROME.value]
hardware_type = [HardwareType.MOBILE__PHONE]
user_agent_rotator = UserAgent(software_names=software_names, hardware_type=hardware_type)
CONFIG = dotenv.dotenv_values()

proxyObject = FreeProxy(country_id=['GB'], rand=True)

INSTOCK = []

def test_webhook():
    """
    Sends a test Discord webhook notification
    """
    data = {
        "username": CONFIG['USERNAME'],
        "avatar_url": CONFIG['AVATAR_URL'],
        "embeds": [{
            "title": "Testing Webhook",
            "description": "This is just a quick test to ensure the webhook works. Thanks again for using these montiors!",,
            "color": int(CONFIG['COLOUR']),
            "footer": {'text': 'Made by Yasser'},
            "timestamp": str(datetime.datetime.utcnow())
        }]
    }

    result = rq.post(CONFIG['WEBHOOK'], data=json.dumps(data), headers={"Content-Type": "application/json"})

    try:
        result.raise_for_status()
    except rq.exceptions.HTTPError as err:
        logging.error(err)
    else:
        print("Payload delivered successfully, code {}.".format(result.status_code))
        logging.info(msg="Payload delivered successfully, code {}.".format(result.status_code))


def discord_webhook(title, url, thumbnail):
    """
    Sends a Discord webhook notification to the specified webhook URL
    """
    data = {
        "username": CONFIG['USERNAME'],
        "avatar_url": CONFIG['AVATAR_URL'],
        "embeds": [{
            "title": title, 
            "url": url,
            "thumbnail": thumbnail,
            "color": CONFIG['COLOUR'],
            "footer": {"text": "Made by Yasser"},
            "timestamp": str(datetime.utcnow()),
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
    for product in INSTOCK:
        if product == item:
            return True
    return False


def scrape_main_site(headers, proxy):
    """
    Scrape the Footlocker site and adds each item to an array
    """
    items = []

    # Makes request to site
    s = requests.Session()
    html = s.get('https://www.footlocker.co.uk/en/men/shoes/', headers=headers, proxies=proxy, verify=False, timeout=10)
    soup = BeautifulSoup(html.text, 'html.parser')
    array = soup.find_all('div', {'class': 'fl-category--productlist--item'})
    
    # Stores particular details in array
    for i in array:
        item = [i.find('span', {'itemprop': 'name'}).text,
                i.find('a')['href'],
                f'https://images.footlocker.com/is/image/FLEU/{i.find("a")["href"].split("=")[1]}?wid=280&hei=280']
        items.append(item)

    logging.info(msg='Successfully scraped site')
    s.close()
    return items


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
            print(item)
            discord_webhook(
                title=item[0],
                url=item[1],
                thumbnail=item[2]
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
    headers = {'User-Agent': user_agent_rotator.get_random_user_agent()}
    
    # Collecting all keywords (if any)
    keywords = CONFIG['KEYWORDS'].split('%')
    while True:
        try:
            # Makes request to site and stores products 
            items = remove_duplicates(scrape_main_site(headers, proxy))
            for item in items:

                if keywords == "":
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
            time.sleep(int(CONFIG['DELAY']))

        except Exception as e:
            print(f"Exception found '{e}' - Rotating proxy and user-agent")
            logging.error(e)

            # Rotates headers
            headers = {'User-Agent': user_agent_rotator.get_random_user_agent()}
            
            if CONFIG['PROXY'] == "":
                # If no optional proxy set, rotates free proxy
                proxy = {"http": proxyObject.get()}
                
            else:
                # if optional proxy set, rotates if there are multiple proxies
                proxy_no = 0 if proxy_no == (len(proxy_list) - 1) else proxy_no + 1
                proxy = {"http": f"https://{proxy_list[proxy_no]}"}


if __name__ == '__main__':
    urllib3.disable_warnings()
    monitor()
