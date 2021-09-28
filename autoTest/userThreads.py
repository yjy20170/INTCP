import time

from testbed.TbThread import atomic, NormalThread, LatchThread
from FileUtils import delFile


threads = []

def threadFunc(cls):
    print('123')
    def wrapper(func):
        name = func.__name__ + 'Thread'
        def wrapped(*args, **kw):
            print('[ User Thread start ] %s' % func.__name__)
            ret = func(*args, **kw)
            print('[ User Thread  end  ] %s' % func.__name__)
            return ret
        # global FuncsDict
        # FuncsDict[func.__name__] = wrapper
        #threads.append(cls(func,name=name))
        return wrapped
    return wrapper

@threadFunc(NormalThread)
def Init(mn, testParam, logPath):
    s2 = mn.getNodeByName('s2')
    pep = mn.getNodeByName('pep')
    h2 = mn.getNodeByName('h2')
    #DEBUG
    intf = pep.connectionsTo(s2)[0][0]
    atomic(pep.cmd)("ifconfig pep-eth1 txqueuelen %d"%(testParam.appParam.txqueuelen))
    atomic(pep.cmd)("ifconfig pep-eth2 txqueuelen %d"%(testParam.appParam.txqueuelen))


    # tc -s -d qdisc show dev pep-eth2
    # print(testParam.max_queue_size)
    cmds, parent = atomic(intf.delayCmds)(max_queue_size=testParam.appParam.max_queue_size,is_change=True,intf=intf)
    for cmd in cmds:
        atomic(intf.tc)(cmd)

@threadFunc(LatchThread)
def Iperf(mn, testParam, logPath):
    if testParam.appParam.get('isManual') or testParam.appParam.get('isRttTest'):
        return
    logFilePath = '%s/%s.txt'%(logPath, testParam.name)
    delFile(logFilePath)
    
    atomic(mn.getNodeByName('h2').cmd)('iperf3 -s -f k -i 1 --logfile %s &'%logFilePath)

    
    if testParam.appParam.midCC != 'nopep':
        atomic(mn.getNodeByName('pep').cmd)('../bash/runpep '+testParam.appParam.midCC+' &')
    
    #time.sleep(5)

    print('sendTime = %ds'%testParam.appParam.sendTime)
    for i in range(testParam.appParam.sendRound):
        print('iperfc loop %d running' %i)
        
        if testParam.linkParams['pep-h2'].itmDown>0:
            atomic(mn.getNodeByName('s2').cmd)('echo a')
            atomic(mn.getNodeByName('pep').cmd)('echo a')
            atomic(mn.configLinkStatus)('s2','pep','up')
            
        atomic(mn.getNodeByName('h1').cmd)('iperf3 -c 10.0.2.1 -f k -C %s -t %d &'%(testParam.appParam.e2eCC,testParam.appParam.sendTime) )
        time.sleep(testParam.appParam.sendTime + 10)

#thread for test rtt
@threadFunc(LatchThread)
def RttTest(mn, testParam, logPath):
    if testParam.appParam.get('isManual') or not testParam.appParam.get('isRttTest'):
        return
    print("rtt test begin...")
    logFilePath = '%s/%s.txt'%(logPath, testParam.name)
    delFile(logFilePath)
    
    if testParam.midCC != 'nopep':
        atomic(mn.getNodeByName('pep').cmd)('../bash/runpep -C '+testParam.midCC+' &')
        
    #atomic(mn.getNodeByName('h2').cmd)('python ../tcp_test/server.py -c %d -rt %d > %s &'%(testParam.rttTestPacket,testParam.rttTotal,logFilePath))
    atomic(mn.getNodeByName('h2').cmd)('python3 ../tcp_test/server.py &')
    
    #atomic(mn.getNodeByName('h1').cmd)('python ../tcp_test/client.py -c %d -rt %d &'%(testParam.rttTestPacket,testParam.rttTotal))
    if testParam.midCC=="nopep":
        limit = 1.5*testParam.rttTotal
    else:
        limit = testParam.rttSat+0.5*testParam.rttTotal
        
    atomic(mn.getNodeByName('h1').cmd)('python3 ../tcp_test/client.py -l %f > %s &'%(limit,logFilePath))
    time.sleep(testParam.sendTime)
    #time.sleep(testParam.rttTestPacket*testParam.rttTotal/1000+10)
