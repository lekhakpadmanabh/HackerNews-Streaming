"""
Usage:

from hn import HNStream

h = HNStream()

for item in h.stream():
    print("Title: ', item['title'])
    print("By user: ", item['by'])
"""

import collections
from lxml import html as lh
import re
import requests
import threading
import time
try:
    import ujson as json
except ImportError:
    import json


__all__ = ['HNStream']


class HNStream(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def get(self, uri):
        cnt=0
        while cnt < 3:
            try:
                response = requests.get(uri)
                if response.status_code == requests.codes.ok:
                    return response.text
            except requests.exceptions.RequestException as e:
                cnt += 1
                time.sleep(2**cnt)
                continue
        return False

    def get_item(self, item_id):
        """
        return type dictionary
        key: type(value)

            title: unicode
            type: unicode
            id: int
            by: unicode
            score: int
            text: unicode
            time: int (unixepoch)
            url: unicode
            kids: list
        """

        uri = 'https://hacker-news.firebaseio.com/v0/item/{}.json'.format(item_id)
        resp = json.loads(self.get(uri))
        return resp if resp else None

    def stream(self):
        itembuffer = collections.deque(60*[None], 60)
        while True:
            raw_html = self.get("http://news.ycombinator.com/newest")
            if not raw_html:
                time.sleep(30)
                continue
            tree = lh.fromstring(raw_html)
            for link in set(tree.xpath(
                  "//a[re:match(@href, 'item\?id=\d+')]/@href",
                  namespaces={"re": "http://exslt.org/regular-expressions"})):
                item_id = re.match(r'item\?id=(\d+)', str(link)).groups()[0]
                if item_id in itembuffer:
                    continue
                itembuffer.append(item_id)
                resp = self.get_item(item_id)
                if not resp:
                    continue
                yield resp
            time.sleep(30) #robots.txt crawl delay 
