import os
from mininet.cli import CLI

from . import TbThread
from . import RealNetwork
from . import linkDnmcThreads # for threadFunc execution

# logPath: where to write the logs
# isManual: open the command line intereface, or wait until the latchThreads end
def run(testParam, logPath, isManual):
    print(testParam.serialize())
    clear()

    mn = RealNetwork.createNet(testParam)
    
    threads = TbThread.TestbedThreads[:]
    if not isManual:
        threads += TbThread.UserThreads
    # print(len(TbThread.TestbedThreads),len(TbThread.UserThreads))
    TbThread.smartStart(threads, (mn, testParam, logPath,) )

    if isManual:
        #TbThread.LatchThread.pretendRunning()
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

    os.system('sudo mn -c >/dev/null 2>&1')
    os.system('sudo killall -9 xterm >/dev/null 2>&1')
