from twisted.internet import defer, task
from twisted.web.client import getPage
import time
import hashlib

hosts = ["http://yahoo.com", "http://google.com", "http://amazon.com",
"http://ibm.com", "http://apple.com"]

start = time.time()

def printExtendedHash(content, host):
    h = hashlib.sha1(content).hexdigest()
    for i in xrange(1000000):
        h = hashlib.sha1(h).hexdigest()
    print h, host


def main(reactor, hosts):
    dlist = []
    for host in hosts:
        d = getPage(host)
        # when we have the content, call printExtendedHash with it
        d.addCallback(printExtendedHash, host)
        dlist.append(d)

    # finish the process when the "queue" is done
    return defer.gatherResults(dlist).addCallback(printElapsedTime)


def printElapsedTime(ignore):
    print "Elapsed Time: %s" % (time.time() - start)


task.react(main, [hosts])