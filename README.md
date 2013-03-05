ijspider
========

simple spider for accessing foaf xml documents across journaling sites.

this spider is really experimental, and does not behave itself very well. It uses the standard
python threading library. although I have tried to get it to behave and respond to keyboard
interrupts, sometimes it won't, so `pgrep py | xargs kill -9` may be required.

motivation
----------

FOAF is an xml (i.e. machine readable) format describing links between people popular on
journaling sites.  I want to mine this data in order to see information about links
between users.


todo
----

 * store data in some cache/sqlite3 db for offline processing
 * get threads to listen to some event for shutdown
 * improve performance, fix queue locking get/put mess 
 * investigate zeromq, multiprocessing and similar

example
-------

`py ijspider.py <username> | egrep --line-buffered --color "<sha1hash>|$"`

