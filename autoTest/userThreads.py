import time

from testbed import Param
from testbed.TbThread import *
from FileUtils import delFile


#@threadFunc(False)
def Init(mn, testParam, logPath):
    for l in testParam.topoParam.linkNames():
        nameA,nameB = l.split(Param.LinkNameSep)
        nodeA = mn.getNodeByName(nameA)
        switch = mn.getNodeByName(l)
        nodeB = mn.getNodeByName(nameB)

        atomic(nodeA.cmd)("ifconfig %s txqueuelen %d"%(l,testParam.appParam.txqueuelen))
        atomic(nodeB.cmd)("ifconfig %s txqueuelen %d"%(nameB+Param.LinkNameSep+nameA,testParam.appParam.txqueuelen))
        
        ### max_queue_size
        # tc -s -d qdisc show dev pep_eth2
        # print(testParam.max_queue_size)
        intf = nodeA.connectionsTo(switch)[0][0]
        cmds, parent = atomic(intf.delayCmds)(max_queue_size=testParam.appParam.max_queue_size,is_change=True,intf=intf)
        for cmd in cmds:
            atomic(intf.tc)(cmd)
        intf = nodeB.connectionsTo(switch)[0][0]
        cmds, parent = atomic(intf.delayCmds)(max_queue_size=testParam.appParam.max_queue_size,is_change=True,intf=intf)
        for cmd in cmds:
            atomic(intf.tc)(cmd)


def kill_intcp_processes(mn,testParam):
    atomic(mn.getNodeByName('h2').cmd)('killall intcps')
    atomic(mn.getNodeByName('h1').cmd)('killall intcpc')
    if testParam.appParam.midCC != 'nopep':
        for node in testParam.topoParam.nodes:
            if not node=='h1' and not node=='h2':
                atomic(mn.getNodeByName(node).cmd)('killall intcpm')
            
@threadFunc(True)
def ThroughputTest(mn,testParam,logPath):
    if testParam.appParam.get('isRttTest'):
        return
    logFilePath = '%s/%s.txt'%(logPath, testParam.name)
    delFile(logFilePath)
    
    if testParam.appParam.get('protocol')=="TCP":      #only support e2e TCP
        atomic(mn.getNodeByName('h2').cmd)('iperf3 -s -f k -i 1 --logfile %s &'%logFilePath)
        for i in range(testParam.appParam.sendRound):
            print('iperfc loop %d running' %i)
            atomic(mn.getNodeByName('h1').cmd)('iperf3 -c 10.0.100.2 -f k -C %s -t %d &'%(testParam.appParam.e2eCC,testParam.appParam.sendTime) )
            time.sleep(testParam.appParam.sendTime + 10)
            
    elif testParam.appParam.get('protocol')=="INTCP":   #only support one round
        for i in range(testParam.appParam.sendRound):
            if testParam.appParam.midCC != 'nopep':
                
                for node in testParam.topoParam.nodes:
                    if node not in ['h1','h2']:
                        # print(node,"run intcpm")
                        atomic(mn.getNodeByName(node).cmd)('../appLayer/intcpApp/intcpm >/dev/null 2>&1 &')
                        time.sleep(2)
            atomic(mn.getNodeByName('h2').cmd)('../appLayer/intcpApp/intcps >/dev/null 2>&1 &')
            atomic(mn.getNodeByName('h1').cmd)('../appLayer/intcpApp/intcpc >> %s &'%logFilePath)
            time.sleep(testParam.appParam.sendTime+10)
            kill_intcp_processes(mn,testParam)
            time.sleep(2)
            
        return
        
#thread for test rtt
@threadFunc(True)
def RttTest(mn, testParam, logPath):
    if not testParam.appParam.get('isRttTest'):
        return
    logFilePath = '%s/%s.txt'%(logPath, testParam.name)
    senderLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"send")
    receiverLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"recv")
    clientLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"client")
    
    delFile(logFilePath)
    delFile(senderLogFilePath)
    delFile(receiverLogFilePath)
    
    #if testParam.midCC != 'nopep':
    #   atomic(mn.getNodeByName('pep').cmd)('../bash/runpep -C '+testParam.midCC+' &')
    #RttTestPacketNum = 1000
    #atomic(mn.getNodeByName('h2').cmd)('python ../tcp_test/server.py -c %d -rt %d > %s &'%(RttTestPacketNum,testParam.rttTotal,logFilePath))
    if testParam.appParam.get('protocol')=="TCP":   # h1->h2
        atomic(mn.getNodeByName('h1').cmd)('python3 ./sniff.py --t > %s &'%(senderLogFilePath))
        atomic(mn.getNodeByName('h2').cmd)('python3 ./sniff.py --t > %s &'%(receiverLogFilePath))
        
        atomic(mn.getNodeByName('h2').cmd)('python3 ../appLayer/tcpApp/server.py >/dev/null 2>&1 &')
        atomic(mn.getNodeByName('h1').cmd)('python3 ../appLayer/tcpApp/client.py -l %f >/dev/null 2>&1 &'%(0))
        time.sleep(testParam.appParam.sendTime)
        
    elif testParam.appParam.get('protocol')=="INTCP":
        
        #time.sleep(1)
        
        if testParam.appParam.midCC != 'nopep':
            
            for node in testParam.topoParam.nodes:
                if not node=='h1' and not node=='h2':
                    # print(node,"run intcpm")
                    atomic(mn.getNodeByName(node).cmd)('../appLayer/intcpApp/intcpm >/dev/null 2>&1 &')
                    time.sleep(2)
                    #atomic(mn.getNodeByName(node).cmd)('../appLayer/intcpApp/intcpm > %s/%s.txt &'%(logPath, testParam.name+"_"+node))

        #atomic(mn.getNodeByName('h2').cmd)('../appLayer/intcpApp/intcps > %s/%s.txt &'%(logPath, testParam.name+"_"+"h2"))
        atomic(mn.getNodeByName('h2').cmd)('python3 ./sniff.py > %s &'%(senderLogFilePath))
        atomic(mn.getNodeByName('h1').cmd)('python3 ./sniff.py > %s &'%(receiverLogFilePath))
        
        atomic(mn.getNodeByName('h2').cmd)('../appLayer/intcpApp/intcps >/dev/null 2>&1 &')
        atomic(mn.getNodeByName('h1').cmd)('../appLayer/intcpApp/intcpc >/dev/null 2>&1 &')
        #atomic(mn.getNodeByName('h1').cmd)('../appLayer/intcpApp/intcpc > %s &'%(clientLogFilePath))
        time.sleep(testParam.appParam.sendTime)
        return

# for intcp only
# @threadFunc(True)
def PerformTest(mn, testParam, logPath):
    if not testParam.appParam.get('protocol')=="INTCP":
        return
    print("performance test begin")
    logFilePath = '%s/%s.txt'%(logPath, testParam.name)
