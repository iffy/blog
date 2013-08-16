from twisted.internet import threads, task
import time

def intenseTask(data):
    print 'work:', data
    time.sleep(0.2)
    print 'done:', data


def main(reactor):
    return threads.deferToThread(intenseTask, 'foo')

task.react(main)