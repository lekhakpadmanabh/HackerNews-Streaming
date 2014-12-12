"""
Usage:

from hn import HNStream

h = HNStream()

for item in h.submission_stream():
    print("Title: ", item['title'])
    print("By user: ", item['by'])
"""

import collections
import functools
from lxml import html as lh
import re
import requests
import time

try:
    import ujson as json
except ImportError:
    import json


__all__ = ['HNStream']


class RetryOnInvalidSchema(object):
    """Decorator to check api response,
    conduct retries and on eventual failure
    return None"""

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
                except AssertionError, TypeError:
                    res = None
                    time.sleep(2 ** tries)
                    tries += 1
                    continue
            return res
        return wrapped


class HNStream(object):
    """
    property:
        crawl_delay: defaults to 30 (seconds), must be  >=30

    public methods:
        get_item(item_id): returns a dictionary for given item_id
        submission_stream(): indefinitely yields new submissions
        comment_stream(): indefinitely yields new comments
    """

    def __init__(self):
        self._crawl_delay = 60
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

    @staticmethod
    def _get(uri):
        try:
            resp = requests.get(uri)
            if resp.status_code == requests.codes.ok:
                return resp.text
            return None
        except requests.exceptions.RequestException:
            return None

    @RetryOnInvalidSchema(KEYS=('by', 'id'), MAX_TRIES=3)
    def _get_api_response(self, uri):
        return json.loads(HNStream._get(uri))

    def get_item(self, item_id):
        """
        See: https://github.com/HackerNews/API#items
        for a description of fields.
        """
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

    def _get_newest(self, uri, xpath_eval):
        raw_html = HNStream._get(uri)
        if not raw_html:
            return None
        items = xpath_eval(raw_html)
        return map(lambda x: re.match(r'item\?id=(\d+)',
                                      x).groups()[0], map(str, items))

    def _get_new_submissions(self):
        return self._get_newest(self.web_url + 'newest',
                                HNStream.submission_xpath)

    def _get_new_comments(self):
        return self._get_newest(self.web_url + 'newcomments',
                                HNStream.comment_xpath)

    def _stream(self, getter):

        itembuffer = collections.deque(60 * [None], 60)

        while True:
            item_ids = getter()
            if not item_ids:
                time.sleep(self.crawl_delay)
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
        yield from self._stream(self._get_new_submissions)

    def comment_stream(self):
        yield from self._stream(self._get_new_comments)
