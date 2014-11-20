"""
Usage:

from hn import HNStream

h = HNStream()

for item in h.stream():
    print "Title: ", item.title
    print "By user: ", item.by
"""

import collections
from lxml import html as lh
import re
import requests
import threading
import time
import ujson as json


__all__ = ['HNStream']


class HackerNewsAPIError(Exception):
    pass


class Item:
    """
    Object representation of JSON response.
    For internal use, should never be
    instantiated by the user. 
    An instance of this class is yielded
    by HNStream.stream() via HackerNews.item

    Attributes:

        title: unicode
        type: unicode
        id: int
        by: unicode
        score: int
        text: unicode
        time: int (unixepoch)
        url: unicdoe
        kids: list
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __str__(self):
        return "{}: {}".format(self.type, self.title)

    __repr__ = __str__


class HackerNews:
    """
    Wrapper to get an item from official
    hacker news api. Not intended to be
    used by user as it does not cover all
    methods of API, only the ones required
    for streaming new stories.

    Method:

        item(item_id): returns an instance of Item class
    """

    def __init__(self):
        self.base_url = 'https://hacker-news.firebaseio.com/v0/'

    def _get(self, uri):
        response = requests.get(uri)
        if response.status_code == requests.codes.ok:
            return json.loads(response.text)
        else:
            raise HackerNewsAPIError('HTTP Error {}'.format(response.status_code))

    def item(self, item_id):
        uri = self.base_url + 'item/{}.json'.format(item_id)
        return Item(**self._get(uri))


class HNStream(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

    def stream(self):
        itembuffer = collections.deque(61*[None],61)
        while True:
            r = requests.get('https://news.ycombinator.com/newest')
            tree = lh.fromstring(r.text)
            # http://stackoverflow.com/a/2756994
            links = tree.xpath("//a[re:match(@href, 'item\?id=\d+')]/@href",
                               namespaces={"re": "http://exslt.org/regular-expressions"})
            links = set(links)
            for link in links:
                item_id = re.match(r'item\?id=(\d+)', str(link)).groups()[0]
                if not item_id in itembuffer:
                    itembuffer.append(item_id)
                    yield HackerNews().item(item_id)
            time.sleep(30) #from robots.txt
