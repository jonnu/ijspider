#!/usr/bin/env python

import re
import sys
import time
import Queue
import urllib2
import urlparse
import datetime
import optparse
import threading
import contextlib

from lxml import etree
from httplib import BadStatusLine
from BeautifulSoup import BeautifulSoup


class FoafQueue(Queue.Queue):

    def __init__(self, maxsize=0):
        Queue.Queue.__init__(self, maxsize)
        self.items = set()

    def _put(self, item):
        if item not in self.items:
            Queue.Queue._put(self, item)
            self.items.add(item)


class FoafSpider(threading.Thread):

    NS = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'foaf': 'http://xmlns.com/foaf/0.1/',
        'ya': 'http://blogs.yandex.ru/schema/foaf/',
        'geo': 'http://www.w3.org/2003/01/geo/wgs84_pos#',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }

    AGENT = 'https://github.com/jonnu/ijspider; code@jonnu.eu'

    def __init__(self, queue, foafs):
        threading.Thread.__init__(self)
        self.queue = queue
        self.foafs = foafs

    def get(self, url):

        try:
            request = urllib2.Request(url)
            request.add_header("User-Agent", self.AGENT)
            context = contextlib.closing(urllib2.urlopen(request))
        except urllib2.HTTPError:
            self.log("404. Skipping...")
            context = False
            pass
        except BadStatusLine:
            self.log("Bad status returned. Skipping...")
            context = False
            pass

        return context

    def process(self, url):

        with_bs = False
        with self.get(url) as foafdata:
            if not foafdata:
                return

            tree = etree.parse(foafdata)
            sha1 = tree.xpath('//foaf:Person/foaf:mbox_sha1sum', namespaces=self.NS)
            if len(sha1) == 0:

                # FOAF document does not have mbox_sha1sum... try get it from html instead
                with self.get('http://%s.insanejournal.com/' % self.get_user(url)) as htmldata:
                    soup = BeautifulSoup(htmldata)
                    tags = soup('meta', {'content': re.compile("foaf:mbox_sha1sum '([0-9a-f]{40})'")})
                    for tag in tags:
                        srch = re.search("'([a-f0-9]{40})'", tag['content'])
                        mbox = srch.group(1)
                        break

                    with_bs = True

            else:
                mbox = sha1[0].text

            user = self.get_user(url)
            self.foafs[user] = mbox

            friends = tree.xpath('//foaf:Person/foaf:knows/foaf:Person', namespaces=self.NS)
            overlap = 0
            for friend in friends:
                foaf = friend.find('{%(rdfs)s}seeAlso' % self.NS).attrib.itervalues().next()

                # Only add new foaf usernames
                if self.get_user(foaf) not in self.foafs:
                    overlap += 1
                    self.queue.put(foaf, True, 0.1)

            self.log("%s: %-20s %-2s(%3d/%3d new, %3d foaf[s], %4d in queue)" % (
                mbox,                    # sha1
                user,                    # username
                '*' if with_bs else '',  # marker to show that we got it with BeautifulSoup, not XPath
                overlap,                 # unique friends (added)
                len(friends),            # total friends
                len(self.foafs),         # number we have processed
                self.queue.qsize()       # current queue size
            ))

        return True

    def log(self, line):

        now = datetime.datetime.now()
        print "%s (%s) | %s" % (
            now.strftime('%Y-%m-%d %H:%M:%S'),
            threading.currentThread().name,
            line
        )

    def run(self):

        while True:

            try:
                url = self.queue.get()
            except Queue.Empty:
                return

            if self.get_user(url) not in self.foafs:
                self.process(url)

            self.queue.task_done()

    @staticmethod
    def make_url(string, domain='insanejournal.com'):
        if domain in string:
            parsed = urlparse.urlparse(string)
            section = 'netloc' if string.startswith('http://') else 'path'
            chunk = getattr(parsed, section)
        else:
            chunk = "%s.%s" % (string, domain)

        return "http://%s/data/foaf" % chunk

    @staticmethod
    def get_user(url, domain='insanejournal.com'):
        user_re = re.compile('^http://(.+?).%s' % domain)
        match = user_re.search(url)
        if match:
            return match.group(1)
        else:
            return None


if __name__ == "__main__":

    threads = 9
    parser = optparse.OptionParser()
    opts, args = parser.parse_args()
    if not args:
        sys.exit('Usage: %s username' % __file__)

    start = time.time()
    foafs = {}
    queue = FoafQueue()
    queue.put(FoafSpider.make_url(args[0]))

    try:
        for i in range(threads):
            t = FoafSpider(queue, foafs)
            t.setDaemon(True)
            t.start()

        queue.join()

    except (KeyboardInterrupt, SystemExit):
        pass

    print "\n\n"
    for mbox, user in foafs.items():
        print "%s | %s" % (mbox, user)

    time.sleep(2)
    print "\nFinished work. (Ran for: %ss)" % (time.time() - start)
