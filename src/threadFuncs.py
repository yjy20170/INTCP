import time
import random
import os

from MultiThread import Thread, atomic

def threadEvent(func):
    def wrapper(*args, **kw):
        print('[ Thread start ] %s' % func.__name__)
        ret = func(*args, **kw)
        print('[ Thread  end  ] %s' % func.__name__)
        return ret
    return wrapper

### thread for dynamic link params control
def generate_bw(meanbw,varbw,prd,policy):
    if policy=="random":
        new_bw = random.uniform(meanbw-varbw,meanbw+varbw)
        return new_bw
    elif policy=="sin":
        cur_time = time.time()
        return meanbw+varbw*math.sin(2*math.pi*cur_time/prd)

@threadEvent
def funcLinkUpdate(mn,netParam):
    if netParam.varBw <= 0:
        return
    s2 = mn.getNodeByName("s2")
    pep = mn.getNodeByName("pep")
    h2 = mn.getNodeByName("h2")
    
    def config(intf,bw,loss=None,delay=None,rtt=None):
        cmds = []
        if bw:
            bwcmds, parent = atomic(intf.bwCmds)(is_change=True,bw=new_bw)
            cmds += bwcmds
        #TODO
        if delay:
            pass
        if rtt:
            pass
            
        tcoutputs = [ atomic(intf.tc)(cmd) for cmd in cmds ]
        
    while not Thread.stopped():
        time.sleep(2)
        new_bw = generate_bw(netParam.bw,netParam.varBw,1,"random")
        for intf in (s2.connectionsTo(pep)[0]+s2.connectionsTo(h2)[0]):
            config(intf,bw=new_bw)

### thread for dynamic link up/down control
@threadEvent
def funcMakeItm(mn,netParam):
    if netParam.prdItm <= 0:
        return
    while not Thread.stopped():
        time.sleep(netParam.prdTotal-netParam.prdItm)
        atomic(mn.configLinkStatus)('s2','pep','down')
        time.sleep(netParam.prdItm)
        atomic(mn.configLinkStatus)('s2','pep','up')

        # if changing s2 - h2
        # mn.getNodeByName("h2").cmd("route add default gw 10.0.2.90 &")

### thread for iperf experiments with/without PEP
@threadEvent
def funcIperfPep(mn,netParam):
    if netParam.pepCC != 'nopep':
        atomic(mn.getNodeByName("pep").cmd)('../bash/runpep '+netParam.pepCC+' &')
    try:
        os.remove('../logs/log_'+netParam.toString()+'.txt')
    except:
        pass
    atomic(mn.getNodeByName("h2").cmd)('iperf3 -s -f k -i 10 --logfile ../logs/log_'+netParam.toString()+'.txt &')
    
    print("sendTime = %ds" %(netParam.sendTime))
    for i in range(5):
        print("iperfc loop %d starting" %(i))
        atomic(mn.getNodeByName("h1").cmd)('iperf3 -c 10.0.2.1 -f k -C '+netParam.e2eCC+' -t '+str(netParam.sendTime)+' &')
        #time.sleep(netParam.sendTime + 20)
        #DEBUG
        #mn.getNodeByName("h1").cmd('iperf3 -c 10.0.2.1 -f k -C '+netParam.e2eCC+' -t '+str(netParam.sendTime))
        time.sleep(netParam.sendTime + 20)
