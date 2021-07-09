import time
import random
import os
import math

from MultiThread import Thread, atomic,ReleaserThread

def threadEvent(func):
    def wrapper(*args, **kw):
        print('[ Thread start ] %s' % func.__name__)
        ret = func(*args, **kw)
        print('[ Thread  end  ] %s' % func.__name__)
        return ret
    return wrapper

### thread for dynamic link params control
K = 1
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

@threadEvent
def funcLinkUpdate(mn, netEnv, logPath):
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
            
        tcoutputs = [ atomic(intf.tc)(cmd) for cmd in cmds ]

    global K
    K = 1
    while ReleaserThread.isRunning():
        if netEnv.varMethod != 'squareFreq':
            #newBw = generateBw('random',netEnv.bw,netEnv.varBw)
            newBw = generateBw(netEnv.varMethod, netEnv.bw, netEnv.varBw)
            for intf in (s2.connectionsTo(pep)[0]+s2.connectionsTo(h2)[0]):
                config(intf,bw=newBw)
            time.sleep(netEnv.varIntv)
        else:
            # newBw = generateBw('random',netEnv.bw,netEnv.varBw)
            newBw = generateBw('square', netEnv.bw, netEnv.varBw)
            for intf in (s2.connectionsTo(pep)[0] + s2.connectionsTo(h2)[0]):
                config(intf, bw=newBw)
            time.sleep(2)

            # newBw = generateBw('random',netEnv.bw,netEnv.varBw)
            newBw = generateBw('square', netEnv.bw, netEnv.varBw)
            for intf in (s2.connectionsTo(pep)[0] + s2.connectionsTo(h2)[0]):
                config(intf, bw=newBw)
            time.sleep(netEnv.varIntv)

### thread for dynamic link up/down control
@threadEvent
def funcMakeItm(mn,netEnv, logPath):
    if netEnv.itmDown <= 0:
        return
    while ReleaserThread.isRunning():
        time.sleep(netEnv.itmTotal-netEnv.itmDown)
        atomic(mn.configLinkStatus)('s2','pep','down')
        time.sleep(netEnv.itmDown)
        atomic(mn.configLinkStatus)('s2','pep','up')

        # if changing s2 - h2
        # mn.getNodeByName('h2').cmd('route add default gw 10.0.2.90 &')

### thread for iperf experiments with/without PEP
@threadEvent
def funcIperfPep(mn,netEnv, logPath):
    if netEnv.pepCC != 'nopep':
        atomic(mn.getNodeByName('pep').cmd)('../bash/runpep '+netEnv.pepCC+' &')
    atomic(mn.getNodeByName('h2').cmd)('iperf3 -s -f k -i 1 --logfile %s/%s.txt &'%(logPath,netEnv.name))
    
    print('sendTime = %ds'%netEnv.sendTime)
    for i in range(3):
        print('iperfc loop %d starting' %i)
        atomic(mn.getNodeByName('h1').cmd)('iperf3 -c 10.0.2.1 -f k -C %s -t %d &'%(netEnv.e2eCC,netEnv.sendTime) )
        #time.sleep(netEnv.sendTime + 20)
        #DEBUG
        #mn.getNodeByName('h1').cmd('iperf3 -c 10.0.2.1 -f k -C %s -t %d'%(netEnv.e2eCC,netEnv.sendTime))
        time.sleep(netEnv.sendTime + 20)
