import os
from mininet.cli import CLI

from . import linkDnmcThreads
from . import TbThread
from . import RealNetwork

# net: topo of net
# userThreads: things to run on this testbed (transport & application layer)
# logPath: where to write the logs
# isManual: open the command line intereface, or wait until the latchThreads end
def run(testParam, logPath):
    print(testParam.serialize())
    clear()

    mn = RealNetwork.createNet(testParam)

    #threads = testParam.appParam.threads+linkDnmcThreads.threads
    threads = testParam.appParam.threads
    
    TbThread.smartStart(threads, (mn, testParam, logPath,) )

    if testParam.appParam.isManual:
        # enter command line interface...
        CLI(mn)
    else:
        # normal threads keep running until latchThread ends
        for thread in threads:
            thread.join()

        # terminate
        mn.stop()

    return

def clear():
    TbThread.clear()

    os.system('mn -c >/dev/null 2>&1')
    os.system('killall -9 xterm >/dev/null 2>&1')
