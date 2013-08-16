from threading import Thread
from time import sleep

class Worker(Thread):

    def __init__(self, name):
        Thread.__init__(self)
        self._name = name

    def run(self):
        while True:
            print self._name
            sleep(0.1)


for i in xrange(0, 3):
    worker = Worker('worker %d' % (i,))
    worker.setDaemon(True)
    worker.start()

sleep(0.5)