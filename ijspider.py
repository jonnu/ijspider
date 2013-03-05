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


class FoafSpider(threading.Thread):

    NS = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'foaf': 'http://xmlns.com/foaf/0.1/',
        'ya': 'http://blogs.yandex.ru/schema/foaf/',
        'geo': 'http://www.w3.org/2003/01/geo/wgs84_pos#',
        'dc': 'http://purl.org/dc/elements/1.1/'
    }

    AGENT = 'Mozilla/6.0 (Windows NT 6.2; WOW64; rv:16.0.1) Gecko/20121011 Firefox/16.0.1'

    def __init__(self, queue, foafs):
        threading.Thread.__init__(self)
        self.queue = queue
        self.foafs = foafs

    def run(self):

        while True:
            url = self.queue.get()
            now = datetime.datetime.now()

            try:
                request = urllib2.Request(url)
                request.add_header("User-Agent", self.AGENT)
                context = contextlib.closing(urllib2.urlopen(request))
            except urllib2.HTTPError:
                print "404, ignore this"
                self.queue.task_done()
                return

            with context as foafdata:
                tree = etree.parse(foafdata)
                sha1 = tree.xpath('//foaf:Person/foaf:mbox_sha1sum', namespaces=self.NS)
                if len(sha1) == 0:
                    print "No FOAF here...Skipping."
                    self.queue.task_done()
                    return

                user = self.get_user(url)
                mbox = sha1[0].text
                self.foafs[user] = mbox

            friends = tree.xpath('//foaf:Person/foaf:knows/foaf:Person', namespaces=self.NS)
            overlap = 0
            for friend in friends:
                foaf = friend.find('{%(rdfs)s}seeAlso' % self.NS).attrib.itervalues().next()
                #print "enqueuing %s" % self.get_user(foaf)
                foafuser = self.get_user(foaf)
                if foafuser in self.foafs:
                    overlap += 1
                    #print "%s already processed" % foafuser
                else:
                    self.queue.put(foaf)

            #time.sleep(random.randint(1, 2)) %03.2f {:03.2f}
            print "%s | %s: %-20s (%3d/%3d friends, %3d foaf[s], %4d in queue)" % (now.strftime('%Y-%m-%d %H:%M:%S'), mbox, user, len(friends)-overlap, len(friends), len(self.foafs), self.queue.qsize())
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

    threads = 8
    parser = optparse.OptionParser()
    opts, args = parser.parse_args()
    if not args:
        sys.exit('Usage: %s username' % __file__)

    start = time.time()
    foafs = {}
    queue = Queue.Queue()
    queue.put(FoafSpider.make_url(args[0]))

    try:
        for i in range(threads):
            t = FoafSpider(queue, foafs)
            t.setDaemon(True)
            t.start()
            t.join(5)

        queue.join()

    except (KeyboardInterrupt, SystemExit):
        pass

    print "\n\n"
    for mbox, user in foafs.items():
        print "%s | %s" % (mbox, user)

    time.sleep(2)
    print "\nFinished work. (Ran for: %ss)" % (time.time() - start)
