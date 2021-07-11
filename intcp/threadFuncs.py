import time
import random
import math

from MultiThread import atomic, LatchThread
from Utils import delFile
# FuncsDict = {}

def threadFunc(func):
    def wrapper(*args, **kw):
        print('[ Thread start ] %s' % func.__name__)
        ret = func(*args, **kw)
        print('[ Thread  end  ] %s' % func.__name__)
        return ret
    # global FuncsDict
    # FuncsDict[func.__name__] = wrapper
    return wrapper

### thread for dynamic link params control
K = 0
def generateBw(policy, meanbw,varbw, prd=10):
    if policy=='random':
        new_bw = random.uniform(meanbw-varbw,meanbw+varbw)
        return new_bw
    elif policy=='sin':
        cur_time = time.time()
        return meanbw+varbw*math.sin(2*math.pi*cur_time/prd)
    elif policy == 'square':
        global K
        newBw = meanbw + varbw * K
        K = -1*K
        return newBw
    else:
        raise Exception

@threadFunc
def LinkUpdate(mn, netEnv, logPath):
    if netEnv.varBw <= 0:
        return
    s2 = mn.getNodeByName('s2')
    pep = mn.getNodeByName('pep')
    h2 = mn.getNodeByName('h2')
    
    def config(intf,bw=None,rtt=None,loss=None):
        cmds = []
        if bw:
            bwcmds, parent = atomic(intf.bwCmds)(is_change=True,bw=bw)
            cmds += bwcmds
        #TODO
        if rtt:
            pass
        if loss:
            pass
        for cmd in cmds:
            atomic(intf.tc)(cmd)

    global K
    K = 1
    while LatchThread.isRunning():
        if netEnv.varMethod in ['squareHighPulse', 'squareLowPulse']:
            # newBw = generateBw('random',netEnv.bw,netEnv.varBw)
            newBw = generateBw('square', netEnv.bw, netEnv.varBw)
            for intf in (s2.connectionsTo(pep)[0] + s2.connectionsTo(h2)[0]):
                config(intf, bw=newBw)
            if netEnv.varMethod == 'squareHighPulse':
                time.sleep(5)
            else:
                time.sleep(netEnv.varIntv)

            # newBw = generateBw('random',netEnv.bw,netEnv.varBw)
            newBw = generateBw('square', netEnv.bw, netEnv.varBw)
            for intf in (s2.connectionsTo(pep)[0] + s2.connectionsTo(h2)[0]):
                config(intf, bw=newBw)
            if netEnv.varMethod == 'squareHighPulse':
                time.sleep(netEnv.varIntv)
            else:
                time.sleep(5)
        else:
            #newBw = generateBw('random',netEnv.bw,netEnv.varBw)
            newBw = generateBw(netEnv.varMethod, netEnv.bw, netEnv.varBw)
            for intf in (s2.connectionsTo(pep)[0]+s2.connectionsTo(h2)[0]):
                config(intf,bw=newBw)
            time.sleep(netEnv.varIntv)

### thread for dynamic link up/down control
@threadFunc
def MakeItm(mn, netEnv, logPath):
    if netEnv.itmDown <= 0:
        return
    while LatchThread.isRunning():
        time.sleep(netEnv.itmTotal-netEnv.itmDown)
        atomic(mn.configLinkStatus)('s2','pep','down')
        time.sleep(netEnv.itmDown)
        atomic(mn.configLinkStatus)('s2','pep','up')

        # if changing s2 - h2
        # mn.getNodeByName('h2').cmd('route add default gw 10.0.2.90 &')

### thread for iperf experiments with/without PEP
@threadFunc
def IperfPep(mn, netEnv, logFolderPath):
    if netEnv.pepCC != 'nopep':
        atomic(mn.getNodeByName('pep').cmd)('../bash/runpep '+netEnv.pepCC+' &')
    logFilePath = '%s/%s.txt'%(logFolderPath, netEnv.name)
    delFile(logFilePath)
    atomic(mn.getNodeByName('h2').cmd)('iperf3 -s -f k -i 1 --logfile %s &'%logFilePath)
    
    print('sendTime = %ds'%netEnv.sendTime)
    # TODO
    # only one time
    for i in range(1):
        print('iperfc loop %d running' %i)
        atomic(mn.getNodeByName('h1').cmd)('iperf3 -c 10.0.2.1 -f k -C %s -t %d &'%(netEnv.e2eCC,netEnv.sendTime) )
        #time.sleep(netEnv.sendTime + 20)
        #DEBUG
        #mn.getNodeByName('h1').cmd('iperf3 -c 10.0.2.1 -f k -C %s -t %d'%(netEnv.e2eCC,netEnv.sendTime))
        time.sleep(netEnv.sendTime + 20)
