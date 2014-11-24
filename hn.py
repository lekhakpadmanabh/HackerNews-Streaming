"""
Usage:

from hn import HNStream

h = HNStream()

for item in h.stream():
    print("Title: ", item['title'])
    print("By user: ", item['by'])
"""

import collections
import functools
from lxml import html as lh
import re
import requests
import threading
import time
try:
    import ujson as json
except ImportError:
    import json


__all__ = ['SubmissionStream']


class RetryOnInvalidSchema(object):
    """Decorator that ensures that api response
    is as expected, if not it retries to get appropriate
    response. If appropriate response is not received
    it returns None so that it can be caught by an if"""

    def __init__(self, KEYS, MAX_TRIES):

        self.KEYS = KEYS
        self.MAX_TRIES = MAX_TRIES

    def __call__(self, func):

        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            tries = 0
            while tries < self.MAX_TRIES:
                try:
                    res = func(*args, **kwargs)
                    for key in self.KEYS:
                        assert key in res
                    break
                except AssertionError:
                    res = None
                    time.sleep(2**tries)
                    tries += 1
                    continue
            return res
        return wrapped


class HNBase(object):

    def __init__(self):

        self._crawl_delay = 30
        self.api_url = 'https://hacker-news.firebaseio.com/v0/'
        self.web_url = 'https://news.ycombinator.com/'

    @property
    def crawl_delay(self):
        return self._crawl_delay

    @crawl_delay.setter
    def crawl_delay(self, value):
        if value < 30:
            raise ValueError("Forbidden by robots.txt")
        else:
            self._crawl_delay = value

    def _get(self, uri):
        resp = requests.get(uri)
        if resp.status_code == requests.codes.ok:
            return resp.text
        else:
            return None

    @RetryOnInvalidSchema(KEYS=('by', 'id'), MAX_TRIES=3)
    def _get_api_response(self, uri):
        return json.loads(self._get(uri))

    def get_item(self, item_id):
        uri = self.api_url + 'item/{}.json'.format(item_id)
        resp = self._get_api_response(uri)
        return resp

    @staticmethod
    def submission_xpath(raw_html):
        return set(lh.fromstring(raw_html).xpath(
                  "//a[re:match(@href, 'item\?id=\d+')]/@href",
                  namespaces={"re": "http://exslt.org/regular-expressions"}))

    @staticmethod
    def comment_xpath(raw_html):
        return lh.fromstring(raw_html).xpath('//a[text()="link"]/@href')

    def get_newest_submissions(self):
        return self._get_newest(self.web_url + 'newest', 
                                HNBase.submission_xpath)

    def get_newest_comments(self):
        return self._get_newest(self.web_url + 'newcomments', 
                                HNBase.comment_xpath)

    def _get_newest(self, uri, xpath_eval):
        raw_html = self._get(uri)
        if not raw_html:
            return None
        items = xpath_eval(raw_html)
        return map(lambda x: re.match(r'item\?id=(\d+)',
                                      x).groups()[0], map(str, items))

    def _stream(self, getter):

        itembuffer = collections.deque(60*[None], 60)

        while True:
            item_ids = getter()
            if not item_ids:
                time.sleep(self.craw_delay)
                continue
            for item_id in item_ids:
                if item_id in itembuffer:
                    continue
                itembuffer.append(item_id)
                resp = self.get_item(item_id)
                if not resp:
                    continue
                yield resp
            time.sleep(self.crawl_delay) 

    def submission_stream(self):
        yield from self._stream(self.get_newest_submissions)

    def comment_stream(self):
        yield from self._stream(self.get_newest_comments)
