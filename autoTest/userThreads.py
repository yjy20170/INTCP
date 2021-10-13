import time

from testbed.TbThread import atomic, NormalThread, LatchThread
from FileUtils import delFile


threads = []

def threadFunc(cls):
    #print('123')
    def wrapper(func):
        name = func.__name__ + 'Thread'
        def wrapped(*args, **kw):
            print('[ User Thread start ] %s' % func.__name__)
            ret = func(*args, **kw)
            print('[ User Thread  end  ] %s' % func.__name__)
            return ret
        # global FuncsDict
        # FuncsDict[func.__name__] = wrapper
        threads.append(cls(func,name=name))
        return wrapped
    return wrapper

#@threadFunc(NormalThread)
def Init(mn, testParam, logPath):
    for l in testParam.linkParams:
        nameA,nameB = l.split('-')
        nodeA = mn.getNodeByName(nameA)
        switch = mn.getNodeByName(l)
        nodeB = mn.getNodeByName(nameB)

        atomic(nodeA.cmd)("ifconfig %s txqueuelen %d"%(l,testParam.appParam.txqueuelen))
        atomic(nodeB.cmd)("ifconfig %s txqueuelen %d"%(nameB+'-'+nameA,testParam.appParam.txqueuelen))
        
        ### max_queue_size
        # tc -s -d qdisc show dev pep-eth2
        # print(testParam.max_queue_size)
        intf = nodeA.connectionsTo(switch)[0][0]
        cmds, parent = atomic(intf.delayCmds)(max_queue_size=testParam.appParam.max_queue_size,is_change=True,intf=intf)
        for cmd in cmds:
            atomic(intf.tc)(cmd)
        intf = nodeB.connectionsTo(switch)[0][0]
        cmds, parent = atomic(intf.delayCmds)(max_queue_size=testParam.appParam.max_queue_size,is_change=True,intf=intf)
        for cmd in cmds:
            atomic(intf.tc)(cmd)

#@threadFunc(LatchThread)
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
    
    #if testParam.midCC != 'nopep':
    #    atomic(mn.getNodeByName('pep').cmd)('../bash/runpep -C '+testParam.midCC+' &')
        
    #atomic(mn.getNodeByName('h2').cmd)('python ../tcp_test/server.py -c %d -rt %d > %s &'%(testParam.rttTestPacket,testParam.rttTotal,logFilePath))
    if testParam.appParam.get('protocol')=="TCP":
        atomic(mn.getNodeByName('h2').cmd)('python3 ../appLayer/tcpApp/server.py &')
        
        #atomic(mn.getNodeByName('h1').cmd)('python ../tcp_test/client.py -c %d -rt %d &'%(testParam.rttTestPacket,testParam.rttTotal))
        
        #if testParam.midCC=="nopep":
        #    limit = 1.5*testParam.rttTotal
        #else:
        #    limit = testParam.rttSat+0.5*testParam.rttTotal
        limit = 0     
        atomic(mn.getNodeByName('h1').cmd)('python3 ../appLayer/tcpApp/client.py -l %f > %s &'%(limit,logFilePath))
        time.sleep(testParam.appParam.sendTime)
        #time.sleep(testParam.rttTestPacket*testParam.rttTotal/1000+10)
    elif testParam.appParam.get('protocol')=="INTCP":
        
        #time.sleep(1)
        
        if testParam.appParam.midCC != 'nopep':
            '''
            if testParam.absTopoParam.name=="net_hmh":
                atomic(mn.getNodeByName('pep').cmd)('../appLayer/intcpApp/intcpm &')
                #atomic(mn.getNodeByName('pep').cmd)('../appLayer/intcpApp/intcpm > %s/%s.txt &'%(logPath, testParam.name+"mid"))
            elif testParam.absTopoParam.name=="net_hmmh":
                atomic(mn.getNodeByName('pep1').cmd)('../appLayer/intcpApp/intcpm &')
                atomic(mn.getNodeByName('pep2').cmd)('../appLayer/intcpApp/intcpm &')
            '''
            for node in testParam.absTopoParam.nodes:
                if not node=='h1' and not node=='h2':
                    atomic(mn.getNodeByName(node).cmd)('../appLayer/intcpApp/intcpm >/dev/null 2>&1 &')
                    
        #atomic(mn.getNodeByName('h2').cmd)('../appLayer/intcpApp/intcps > %s/%s.txt &'%(logPath, testParam.name+"server"))
        atomic(mn.getNodeByName('h2').cmd)('../appLayer/intcpApp/intcps >/dev/null 2>&1 &')
        atomic(mn.getNodeByName('h1').cmd)('../appLayer/intcpApp/intcpc > %s &'%(logFilePath))
        time.sleep(testParam.appParam.sendTime)
        return

