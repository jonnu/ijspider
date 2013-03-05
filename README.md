ijspider
========

simple spider for accessing foaf xml documents across journaling sites.

this spider is really experimental, and does not behave itself very well. It uses the standard
python threading library. although I have tried to get it to behave and respond to keyboard
interrupts, sometimes it won't, so `pgrep py | xargs kill -9` may be required.
