"""
Usage:

from hn import HNStream

h = HNStream()

for item in h.stream():
    print "Title: ", item.title
    print "By user: ", item.by
"""

from lxml import html as lh
import re
import requests
import threading
import time
import ujson as json


__all__ = ['HNStream']


class Item:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class HackerNews:

    def __init__(self):
        self.base_url = 'https://hacker-news.firebaseio.com/v0/{api}'

    def get(self, uri):
        response = requests.get(uri)
        if response.status_code == requests.codes.ok:
            return json.loads(response.text)
        else:
            raise Exception('HTTP Error {}'.format(response.status_code))

    def item(self, item_id):
        uri = self.base_url.format(**{'api': 'item/{}.json'.format(item_id)})
        return Item(**self.get(uri))


class SimpleFIFO:

    def __init__(self, length):
        self.length = length
        self.values = length * [None]

    def contains(self, iid):
        return iid in self.values

    def append(self, value):
        assert isinstance(value, str), "Only append strings"
        self.values.append(value)
        while len(self.values) > self.length:
            self.values.pop(0)
        assert len(self.values) == self.length

    def __str__(self):
        return str(self.values)


class HNStream(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def stream(self):

        itembuffer = SimpleFIFO(length=30)
        while True:
            r = requests.get('https://news.ycombinator.com/newest')
            tree = lh.fromstring(r.text)
            # http://stackoverflow.com/a/2756994
            links = tree.xpath("//a[re:match(@href, 'item\?id=\d+')]/@href",
                               namespaces={"re": "http://exslt.org/regular-expressions"})
            links = set(links)
            for link in links:
                iid = re.match(r'item\?id=(\d+)', str(link)).groups()[0]
                if not itembuffer.contains(iid):
                    itembuffer.append(iid)
                    yield HackerNews().item(iid)
            time.sleep(30)
