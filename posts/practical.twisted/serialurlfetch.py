import urllib2
import time
import hashlib

hosts = ["http://yahoo.com", "http://google.com", "http://amazon.com",
"http://ibm.com", "http://apple.com"]

start = time.time()
#grabs urls of hosts and prints first 1024 bytes of page
for host in hosts:
    url = urllib2.urlopen(host)
    print hashlib.sha1(url.read()).hexdigest(), host

print "Elapsed Time: %s" % (time.time() - start)