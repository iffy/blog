import datetime


def run(what):
    now = datetime.datetime.now()
    print '%s says Hello World at time: %s' % (what, now)


for i in range(2):
    run(i)