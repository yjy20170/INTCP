from asyncio import protocols
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
        if not testParam.appParam.dynamic:     #static topo
            for node in testParam.topoParam.nodes:
                if node not in ['h1','h2']:
                    atomic(mn.getNodeByName(node).cmd)('killall intcpm')
        else:   #dynamic topo
            max_midnodes,total_midnodes,isls,links_params = testParam.topoParam
            nodes = ['m%d'%(i+1) for i in range(total_midnodes)]+['gs1','gs2']
            for node in nodes:
                atomic(mn.getNodeByName(node).cmd)('killall intcpm')

def kill_pep_processes(mn,testParam):
    atomic(mn.getNodeByName('h2').cmd)('killall iperf3')
    atomic(mn.getNodeByName('h1').cmd)('killall iperf3')
    if testParam.appParam.midCC != 'nopep':
        if not testParam.appParam.dynamic:  #static topo
            for node in testParam.topoParam.nodes:
                if node not in ['h1','h2']:
                    atomic(mn.getNodeByName(node).cmd)('killall pepsal')
        else:   #dynamic topo
            for node in ['gs1','gs2']:
                atomic(mn.getNodeByName(node).cmd)('killall pepsal')

def start_midnode_processes(mn,testParam,useTCP,pep_nodelay=0):
    if testParam.appParam.midCC != 'nopep':
        if useTCP:      # tcp => open pepsal on gs1 and gs2 
            for node in ['gs1','gs2']:
                atomic(mn.getNodeByName(node).cmd)(f'../pepsal_min/bash/runpep {testParam.appParam.midCC} {pep_nodelay} >/dev/null 2>&1 &')
                time.sleep(2)
        else:           # intcp => open intcpm on ground station and satellites
            if not testParam.appParam.dynamic:      #static topo
                for node in testParam.topoParam.nodes:
                    if node not in ['h1','h2','dummy']: #dummy node for flow test
                        atomic(mn.getNodeByName(node).cmd)('../appLayer/intcpApp/intcpm >/dev/null 2>&1 &')
                        time.sleep(1)
            else:   #dynamic topo
                max_midnodes,total_midnodes,isls,links_params = testParam.topoParam
                nodes = ['gs1','gs2']+['m%d'%(i+1) for i in range(total_midnodes)]
                for node in nodes:
                    atomic(mn.getNodeByName(node).cmd)('../appLayer/intcpApp/intcpm >/dev/null 2>&1 &')
                    time.sleep(1)
                #if testParam.appParam.dynamic_intv > total_midnodes:
                #    time.sleep(testParam.appParam.dynamic_intv-total_midnodes)  #avoid the first link change
    else:
        '''
        for node in ['m%d'%(10*i+9) for i in range(1)]:
            atomic(mn.getNodeByName(node).cmd)('../appLayer/intcpApp/intcpm >/dev/null 2>&1 &')
            time.sleep(1)
        '''
        if testParam.appParam.dynamic:
            time.sleep(2)   #wait the dynamic update thread to set route

@threadFunc(True)
def ThroughputTest(mn,testParam,logPath):
    if testParam.appParam.test_type not in ["throughputTest","throughputWithTraffic"]:
        return
    logFilePath = '%s/%s.txt'%(logPath, testParam.name)
    delFile(logFilePath)
    
    useTCP = testParam.appParam.get('protocol')=="TCP"
    for i in range(testParam.appParam.sendRound): #TODO log is overwritten now
        #NOTE open pep; cleaript
        start_midnode_processes(mn,testParam,useTCP)
        if not testParam.appParam.dynamic and 'dummy' in testParam.topoParam.nodes:
            atomic(mn.getNodeByName('h2').cmd)('echo -e "\nbytes before test:\c" > %s'%(logFilePath))
            atomic(mn.getNodeByName('h2').cmd)('cat /sys/class/net/h2_dummy/statistics/tx_bytes >> %s'%(logFilePath))
        if useTCP:      #only support e2e TCP1
            #print("2")
            atomic(mn.getNodeByName('h1').cmd)('iperf3 -s -f k -i 1 --logfile %s &'%logFilePath)
            time.sleep(1)
            atomic(mn.getNodeByName('h2').cmd)('iperf3 -c 10.0.1.1 -f k -C %s -t %d &'%(testParam.appParam.e2eCC,testParam.appParam.sendTime) )
        else:
            atomic(mn.getNodeByName('h2').cmd)('../appLayer/intcpApp/intcps >/dev/null 2>&1 &')
            time.sleep(1)
            atomic(mn.getNodeByName('h1').cmd)('../appLayer/intcpApp/intcpc >> %s &'%logFilePath)
        time.sleep(testParam.appParam.sendTime + 5)
        if not testParam.appParam.dynamic and 'dummy' in testParam.topoParam.nodes:
            atomic(mn.getNodeByName('h2').cmd)('echo -e "\nbytes after test: \c" >> %s'%(logFilePath))
            atomic(mn.getNodeByName('h2').cmd)('cat /sys/class/net/h2_dummy/statistics/tx_bytes >> %s'%(logFilePath))
        if testParam.appParam.sendRound>1:
            if useTCP:
                kill_pep_processes(mn,testParam)
            else:
                kill_intcp_processes(mn,testParam)
        time.sleep(1)
            
    return
        
#thread for test rtt
@threadFunc(True)
def OwdTest(mn, testParam, logPath):
    if not testParam.appParam.test_type=="owdTest":
        return
    logFilePath = '%s/%s.txt'%(logPath, testParam.name)
    senderLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"send")
    receiverLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"recv")
    clientLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"client")
    
    delFile(logFilePath)
    delFile(senderLogFilePath)
    delFile(receiverLogFilePath)
    
    #RttTestPacketNum = 1000
    #atomic(mn.getNodeByName('h2').cmd)('python ../tcp_test/server.py -c %d -rt %d > %s &'%(RttTestPacketNum,testParam.rttTotal,logFilePath))
    useTCP = testParam.appParam.get('protocol')=="TCP"
    start_midnode_processes(mn,testParam,useTCP,pep_nodelay=1)
                
    # h2 -> h1 for both TCP and INTCP test
    if useTCP:
        if False:   # transport layer owd, which can not support pep now
            atomic(mn.getNodeByName('h1').cmd)('python3 ./sniff.py --t > %s &'%(receiverLogFilePath))
            atomic(mn.getNodeByName('h2').cmd)('python3 ./sniff.py --t > %s &'%(senderLogFilePath))
            time.sleep(1)
            atomic(mn.getNodeByName('h1').cmd)('python3 ../appLayer/tcpApp/server.py >/dev/null 2>&1 &')
            atomic(mn.getNodeByName('h2').cmd)('python3 ../appLayer/tcpApp/client.py -l %f >/dev/null 2>&1 &'%(0))
        else:       # app layer owd
            atomic(mn.getNodeByName('h1').cmd)('python3 ../appLayer/tcpApp/server.py > %s &'%(logFilePath))
            atomic(mn.getNodeByName('h2').cmd)('python3 ../appLayer/tcpApp/client.py -l %f >/dev/null 2>&1 &'%(0))
    else:
        atomic(mn.getNodeByName('h2').cmd)('python3 ./sniff.py > %s &'%(senderLogFilePath))
        atomic(mn.getNodeByName('h1').cmd)('python3 ./sniff.py > %s &'%(receiverLogFilePath))
        time.sleep(1)
        atomic(mn.getNodeByName('h2').cmd)('../appLayer/intcpApp/intcps >/dev/null 2>&1 &')
        atomic(mn.getNodeByName('h1').cmd)('../appLayer/intcpApp/intcpc >/dev/null 2>&1 &')
    #atomic(mn.getNodeByName('h1').cmd)('../appLayer/intcpApp/intcpc > %s &'%(clientLogFilePath))
    time.sleep(testParam.appParam.sendTime + 5)
    return

@threadFunc(True)
def TrafficTest(mn, testParam, logPath):
    if not testParam.appParam.test_type=="trafficTest":
        return
    logFilePath = '%s/%s.txt'%(logPath, testParam.name)
    delFile(logFilePath)
    useTCP = testParam.appParam.get('protocol')=="TCP"
    start_midnode_processes(mn,testParam,useTCP,pep_nodelay=1)
    data_size = testParam.appParam.data_size
    if useTCP:
        a = 1   #do nothing
        atomic(mn.getNodeByName('h2').cmd)('cat /sys/class/net/h2_dummy/statistics/tx_bytes > %s'%(logFilePath))
        atomic(mn.getNodeByName('h1').cmd)('python3 ../appLayer/tcpApp/server.py >/dev/null 2>&1 &')
        atomic(mn.getNodeByName('h2').cmd)('python3 ../appLayer/tcpApp/client.py -f %f >/dev/null 2>&1 &'%(data_size))
        time.sleep(testParam.appParam.sendTime)
        atomic(mn.getNodeByName('h2').cmd)('cat /sys/class/net/h2_dummy/statistics/tx_bytes >> %s'%(logFilePath))
    else:
        atomic(mn.getNodeByName('h2').cmd)('cat /sys/class/net/h2_dummy/statistics/tx_bytes > %s'%(logFilePath))
        atomic(mn.getNodeByName('h2').cmd)('../appLayer/intcpApp/intcps >/dev/null 2>&1 &')
        atomic(mn.getNodeByName('h1').cmd)('../appLayer/intcpApp/intcpc >/dev/null 2>&1 &') 
        time.sleep(testParam.appParam.sendTime)
        atomic(mn.getNodeByName('h2').cmd)('cat /sys/class/net/h2_dummy/statistics/tx_bytes >> %s'%(logFilePath))
    return

@threadFunc(True)
def owdThrpBalanceTest(mn, testParam, logPath):
    if not testParam.appParam.test_type in ["owdThroughputBalance","throughputWithOwd"]:
        return
    logFilePath = '%s/%s.txt'%(logPath, testParam.name)
    thrpLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"thrp")
    senderLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"send")
    receiverLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"recv")

    delFile(logFilePath)
    delFile(thrpLogFilePath)
    delFile(senderLogFilePath)
    delFile(receiverLogFilePath)

    useTCP = testParam.appParam.get('protocol')=="TCP"
    start_midnode_processes(mn,testParam,useTCP,pep_nodelay=1)
    
    if useTCP:
        #atomic(mn.getNodeByName('h2').cmd)('python3 ./sniff.py --t -l 100000 > %s &'%(senderLogFilePath))
        #atomic(mn.getNodeByName('h1').cmd)('python3 ./sniff.py --t -l 100000 > %s &'%(receiverLogFilePath))
        atomic(mn.getNodeByName('h2').cmd)('python3 ./sniff.py --t  > %s &'%(senderLogFilePath))
        atomic(mn.getNodeByName('h1').cmd)('python3 ./sniff.py --t  > %s &'%(receiverLogFilePath))
        time.sleep(1)
        atomic(mn.getNodeByName('h1').cmd)('iperf3 -s -f k -i 1 --logfile %s &'%(thrpLogFilePath))
        time.sleep(1)
        atomic(mn.getNodeByName('h2').cmd)('iperf3 -c 10.0.1.1 -f k -C %s -t %d &'%(testParam.appParam.e2eCC,testParam.appParam.sendTime) )
    else:
        #atomic(mn.getNodeByName('h2').cmd)('python3 ./sniff.py  -l 50000 > %s &'%(senderLogFilePath))
        #atomic(mn.getNodeByName('h1').cmd)('python3 ./sniff.py  -l 50000 > %s &'%(receiverLogFilePath))
        atomic(mn.getNodeByName('h2').cmd)('python3 ./sniff.py  > %s &'%(senderLogFilePath))
        atomic(mn.getNodeByName('h1').cmd)('python3 ./sniff.py  > %s &'%(receiverLogFilePath))
        time.sleep(1)
        atomic(mn.getNodeByName('h2').cmd)('../appLayer/intcpApp/intcps >/dev/null 2>&1 &')
        time.sleep(1)
        atomic(mn.getNodeByName('h1').cmd)('../appLayer/intcpApp/intcpc >> %s &'%(thrpLogFilePath))
    time.sleep(testParam.appParam.sendTime+5)
    return

'''
@threadFunc(True)
def throughputWithOwdTest(mn, testParam, logPath):
    if not testParam.appParam.test_type=="owdThroughputBalance":
        return
    logFilePath = '%s/%s.txt'%(logPath, testParam.name)
    thrpLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"thrp")
    senderLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"send")
    receiverLogFilePath = '%s/%s_%s.txt'%(logPath, testParam.name,"recv")

    delFile(logFilePath)
    delFile(thrpLogFilePath)
    delFile(senderLogFilePath)
    delFile(receiverLogFilePath)

    useTCP = testParam.appParam.get('protocol')=="TCP"
    start_midnode_processes(mn,testParam,useTCP,pep_nodelay=1)
    
    if useTCP:
        atomic(mn.getNodeByName('h2').cmd)('python3 ./sniff.py --t -l 100000 > %s &'%(senderLogFilePath))
        atomic(mn.getNodeByName('h1').cmd)('python3 ./sniff.py --t -l 100000 > %s &'%(receiverLogFilePath))
        time.sleep(1)
        atomic(mn.getNodeByName('h1').cmd)('iperf3 -s -f k -i 1 --logfile %s &'%(thrpLogFilePath))
        time.sleep(1)
        atomic(mn.getNodeByName('h2').cmd)('iperf3 -c 10.0.1.1 -f k -C %s -t %d &'%(testParam.appParam.e2eCC,testParam.appParam.sendTime) )
    else:
        atomic(mn.getNodeByName('h2').cmd)('python3 ./sniff.py  -l 50000 > %s &'%(senderLogFilePath))
        atomic(mn.getNodeByName('h1').cmd)('python3 ./sniff.py  -l 50000 > %s &'%(receiverLogFilePath))
        time.sleep(1)
        atomic(mn.getNodeByName('h2').cmd)('../appLayer/intcpApp/intcps >/dev/null 2>&1 &')
        time.sleep(1)
        atomic(mn.getNodeByName('h1').cmd)('../appLayer/intcpApp/intcpc >> %s &'%(thrpLogFilePath))
    time.sleep(testParam.appParam.sendTime+5)
    return
'''
# for intcp only
# @threadFunc(True)
'''
def PerformTest(mn, testParam, logPath):
    if not testParam.appParam.get('protocol')=="INTCP":
        return
    print("performance test begin")
    logFilePath = '%s/%s.txt'%(logPath, testParam.name)
'''