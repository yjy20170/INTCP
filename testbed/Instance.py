import os
import time

from mininet.clean import cleanup

from . import TbThread
from . import RealNetwork
from . import linkDnmcThreads # for threadFunc execution


# logPath: where to write the logs
# isManual: open the command line intereface, or wait until the latchThreads end
def run(testParam, logPath, isManual):
    print("cleanup mininet...")
    clear()

    #static
    if not testParam.appParam.dynamic:
        mn = RealNetwork.createNet(testParam)

    #dynamic
    else:
        mn = RealNetwork.create_dynamic_net(testParam.topoParam)

    time.sleep(0.5)

    threads = [t for t in TbThread.Threads
            if not(t.isLatchThread and isManual)]

    if isManual:
        TbThread.latchNumInc()
    for thread in threads:
        #static
        thread.start(mn, testParam, logPath)

        #dynamic
        #thread.start(mn,links_params,isls,logPath)
    if isManual:
        time.sleep(1)
        #mn.openXterm()
        mn.enterCli()
        TbThread.latchNumDec()
    for thread in threads:
        thread.join()
    
    return

def clear():
    # os.system('sudo mn -c >/dev/null 2>&1')
    cleanup()

    os.system('sudo killall -9 xterm >/dev/null 2>&1')

    # os.system('kill -9 `jobs -ps`')
    # os.system('kill -9 $(jobs -p)')
    # os.system('kill $(jobs -l | grep Stopped | cut -d\' \' -f3)')
    os.system("for x in `ps -aux | awk {\'if ($8 == \"Tl\") print $2\'}`; do kill -9 $x; done")

    TbThread.latchNumReset()
