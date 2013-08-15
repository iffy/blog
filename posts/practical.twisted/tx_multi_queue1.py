from twisted.internet import defer, task
from twisted.web.client import getPage
import time
from BeautifulSoup import BeautifulSoup

hosts = ["http://yahoo.com", "http://google.com", "http://amazon.com",
"http://ibm.com", "http://apple.com"]

start = time.time()

def printTitle(content, host):
    soup = BeautifulSoup(content)
    print soup.findAll(['title'])


def main(reactor, hosts):
    dlist = []
    for host in hosts:
        d = getPage(host)
        # when we have the content, call printTitle with it
        d.addCallback(printTitle, host)
        dlist.append(d)

    # finish the process when the "queue" is done
    return defer.gatherResults(dlist).addCallback(printElapsedTime)


def printElapsedTime(ignore):
    print "Elapsed Time: %s" % (time.time() - start)


task.react(main, [hosts])