import os
import time

from mininet.clean import cleanup

from . import TbThread
from . import RealNetwork
from . import linkDnmcThreads # for threadFunc execution

@TbThread.LatchFunc
def Cli(mn):
    time.sleep(0.5)
    mn.enterCli()

# logPath: where to write the logs
# isManual: open the command line intereface, or wait until the latchThreads end
def run(testParam, logPath, isManual):
    mn = RealNetwork.createNet(testParam)

    threads = TbThread.NormalThreads[:]
    if not isManual:
        threads += TbThread.LatchThreads
    try:
        TbThread.smartRun(threads, mn, testParam, logPath)
        if isManual:
            Cli(mn)
        TbThread.waitLatch(threads)
    except KeyboardInterrupt:
        print('\nstopped')

    print("cleanup mininet...")
    # os.system('sudo mn -c >/dev/null 2>&1')
    cleanup()
    
    return

def clear():
    # os.system('sudo mn -c >/dev/null 2>&1')
    cleanup()

    # os.system('sudo killall -9 xterm >/dev/null 2>&1')

    # os.system('kill -9 `jobs -ps`')
    # os.system('kill -9 $(jobs -p)')
    # os.system('kill $(jobs -l | grep Stopped | cut -d\' \' -f3)')
    os.system("for x in `ps -aux | awk {\'if ($8 == \"Tl\") print $2\'}`; do kill -9 $x; done")