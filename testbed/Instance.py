import os
import time

from mininet.clean import cleanup

from . import TbThread
from . import RealNetwork
from . import linkDnmcThreads # for threadFunc execution
from autoTest import get_trace

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
        if testParam.appParam.dynamic_complete: # for topo designed by user
            dynamic_trace = testParam.topoParam
        else:                                   # for real starlink topo
            dynamic_trace = get_trace.get_complete_trace(testParam.topoParam,
                                                    isl_loss=testParam.appParam.dynamic_isl_loss,
                                                    uplink_loss=testParam.appParam.dynamic_isl_loss,
                                                    downlink_loss=testParam.appParam.dynamic_isl_loss,
                                                    ground_link_rtt = testParam.appParam.dynamic_ground_link_rtt,
                                                    uplink_bw = testParam.appParam.dynamic_uplink_bw,
                                                    bw_fluctuation=testParam.appParam.dynamic_bw_fluct)
        mn = RealNetwork.create_dynamic_net(dynamic_trace)

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
