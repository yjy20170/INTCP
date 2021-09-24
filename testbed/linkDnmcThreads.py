import time
import random
import math

from .TbThread import NormalThread, LatchThread, atomic


threads = []

def threadFunc(cls):
    def wrapper(func):
        name = func.__name__ + 'Thread'
        def wrapped(*args, **kw):
            print('[ Testbed Thread start ] %s' % func.__name__)
            ret = func(*args, **kw)
            print('[ Testbed Thread  end  ] %s' % func.__name__)
            return ret
        # global FuncsDict
        # FuncsDict[func.__name__] = wrapper
        threads.append(cls(func,name=name))
        return wrapped
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
        K = -1*K
        newBw = meanbw + varbw * K
        return newBw
    else:
        raise Exception
    
@threadFunc(NormalThread)
def LinkUpdate(mn, testParam, logPath):
    if testParam.linkParams['pep-h2'].varBw <= 0:
        return
    s2 = mn.getNodeByName('s2')
    pep = mn.getNodeByName('pep')
    h2 = mn.getNodeByName('h2')
    
    #TODO we should make sure thar the dynamic network params configuring wil not impact the value of other unchanged params 
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
        if testParam.linkParams['pep-h2'].varMethod in ['squareHighPulse', 'squareLowPulse']:

            # newBw = generateBw('random',testParam.bw,testParam.varBw)
            newBw = generateBw('square', testParam.linkParams['pep-h2'].bw, testParam.linkParams['pep-h2'].varBw)
            for intf in (s2.connectionsTo(pep)[0] + s2.connectionsTo(h2)[0]):
                config(intf, bw=newBw)
            if testParam.linkParams['pep-h2'].varMethod == 'squareHighPulse':
                time.sleep(5)
            else:
                time.sleep(testParam.linkParams['pep-h2'].varIntv)

            # newBw = generateBw('random',testParam.bw,testParam.varBw)
            newBw = generateBw('square', testParam.linkParams['pep-h2'].bw, testParam.linkParams['pep-h2'].varBw)
            for intf in (s2.connectionsTo(pep)[0] + s2.connectionsTo(h2)[0]):
                config(intf, bw=newBw)
            if testParam.linkParams['pep-h2'].varMethod == 'squareHighPulse':
                time.sleep(testParam.linkParams['pep-h2'].varIntv)
            else:
                time.sleep(5)
        else:
            #newBw = generateBw('random',testParam.bw,testParam.varBw)
            newBw = generateBw(testParam.linkParams['pep-h2'].varMethod, testParam.linkParams['pep-h2'].bw, testParam.linkParams['pep-h2'].varBw)
            for intf in (s2.connectionsTo(pep)[0]+s2.connectionsTo(h2)[0]):
                config(intf,bw=newBw)
            time.sleep(testParam.linkParams['pep-h2'].varIntv)


### thread for dynamic link up/down control
@threadFunc(NormalThread)
def MakeItm(mn, testParam, logPath):
    if testParam.linkParams['pep-h2'].itmDown <= 0:
        return
    s2 = mn.getNodeByName('s2')
    pep = mn.getNodeByName('pep')
    while LatchThread.isRunning():
        time.sleep(testParam.linkParams['pep-h2'].itmTotal-testParam.linkParams['pep-h2'].itmDown)
        atomic(s2.cmd)('echo a')
        atomic(pep.cmd)('echo a')
        atomic(mn.configLinkStatus)('s2','pep','down')
        
        time.sleep(testParam.linkParams['pep-h2'].itmDown)
        atomic(s2.cmd)('echo a')
        atomic(pep.cmd)('echo a')
        atomic(mn.configLinkStatus)('s2','pep','up')

        # if changing s2 - h2
        # mn.getNodeByName('h2').cmd('route add default gw 10.0.2.90 &')
