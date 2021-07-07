import time
import random
import os
import math

from MultiThread import Thread, atomic

def threadEvent(func):
    def wrapper(*args, **kw):
        print('[ Thread start ] %s' % func.__name__)
        ret = func(*args, **kw)
        print('[ Thread  end  ] %s' % func.__name__)
        return ret
    return wrapper

### thread for dynamic link params control
def Static():
    ### get the func object by which Static() is called.
    from inspect import currentframe, getframeinfo
    caller = currentframe().f_back
    func_name = getframeinfo(caller)[2]
    # print(func_name)
    caller = caller.f_back
    func = caller.f_locals.get(
        func_name, caller.f_globals.get(
            func_name
        )
    )

    class StaticVars:
        def has(self, varName):
            return hasattr(self, varName)

        def declare(self, varName, value):
            if not self.has(varName):
                setattr(self, varName, value)

    if hasattr(func, "staticVars"):
        return func.staticVars
    else:
        # add an attribute to func
        func.staticVars = StaticVars()
        return func.staticVars

def generateBw(policy, meanbw,varbw, prd=10):
    if policy=='random':
        new_bw = random.uniform(meanbw-varbw,meanbw+varbw)
        return new_bw
    elif policy=='sin':
        cur_time = time.time()
        return meanbw+varbw*math.sin(2*math.pi*cur_time/prd)
    elif policy == 'square':
        Static().declare('k', 1)
        Static().k = 0 - Static().k
        return meanbw + varbw * Static().k

    else:
        raise Exception

@threadEvent
def funcLinkUpdate(mn,netParam, logPath):
    if netParam.varBw <= 0:
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
        
    while not Thread.stopped():
        time.sleep(netParam.varIntv)
        #newBw = generateBw('random',netParam.bw,netParam.varBw)
        newBw = generateBw('square', netParam.bw, netParam.varBw)
        for intf in (s2.connectionsTo(pep)[0]+s2.connectionsTo(h2)[0]):
            config(intf,bw=newBw)

### thread for dynamic link up/down control
@threadEvent
def funcMakeItm(mn,netParam, logPath):
    if netParam.itmDown <= 0:
        return
    while not Thread.stopped():
        time.sleep(netParam.itmTotal-netParam.itmDown)
        atomic(mn.configLinkStatus)('s2','pep','down')
        time.sleep(netParam.itmDown)
        atomic(mn.configLinkStatus)('s2','pep','up')

        # if changing s2 - h2
        # mn.getNodeByName('h2').cmd('route add default gw 10.0.2.90 &')

### thread for iperf experiments with/without PEP
@threadEvent
def funcIperfPep(mn,netParam, logPath):
    if netParam.pepCC != 'nopep':
        atomic(mn.getNodeByName('pep').cmd)('../bash/runpep '+netParam.pepCC+' &')

    atomic(mn.getNodeByName('h2').cmd)('iperf3 -s -f k -i 10 --logfile %s/%s.txt &'%(logPath,netParam.str()))
    
    print('sendTime = %ds'%netParam.sendTime)
    for i in range(5):
        print('iperfc loop %d starting' %i)
        atomic(mn.getNodeByName('h1').cmd)('iperf3 -c 10.0.2.1 -f k -C %s -t %d &'%(netParam.e2eCC,netParam.sendTime) )
        #time.sleep(netParam.sendTime + 20)
        #DEBUG
        #mn.getNodeByName('h1').cmd('iperf3 -c 10.0.2.1 -f k -C %s -t %d'%(netParam.e2eCC,netParam.sendTime))
        time.sleep(netParam.sendTime + 20)
