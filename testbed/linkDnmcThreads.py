import time
import random
import math

from .TbThread import threadFunc, atomic, sleepWithCaution, latchRunning
from . import Param


### thread for dynamic link params control
#TODO K for each link? or independent thread for each link?
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
  

def routeReset(mn,testParam):
    nodes = testParam.topoParam.nodes
    for i in range(len(nodes)-1):
        if i == len(nodes)-2:
            seg = 100
        else:
            seg = i+1
        mn.getNodeByName(nodes[i]).cmd('route add default gw 10.0.%d.2'%seg)
    mn.getNodeByName(nodes[-1]).cmd('route add default gw 10.0.%d.1'%100)
    
@threadFunc(False)
def LinkUpdate(mn, testParam, logPath):
    #TODO make sure that the dynamic network params configuring wil not impact the value of other unchanged params 
    def config(intf,bw=None,rtt=None,loss=None):
        cmds = []
        if bw:
            bwcmds, parent = atomic(intf.bwCmds)(is_change=True,bw=bw)
            cmds += bwcmds
        #TODO add rtt and loss
        if rtt:
            pass
        if loss:
            pass
        for cmd in cmds:
            atomic(intf.tc)(cmd)

    global K
    K = 1
    linkNames = []
    for ln in testParam.topoParam.linkNames():
        if testParam.linksParam.getLP(ln).varBw>0:
            linkNames.append(ln)
            sleeptime = testParam.linksParam.getLP(ln).varIntv
    if linkNames == []:
        return
    while latchRunning():
        for linkName in linkNames:
            nameA,nameB = linkName.split(Param.LinkNameSep)
            nodeA = mn.getNodeByName(nameA)
            switch = mn.getNodeByName(linkName)
            nodeB = mn.getNodeByName(nameB)
            # if testParam.linkParams[linkName].varMethod in ['squareHighPulse', 'squareLowPulse']:
            #     # newBw = generateBw('random',testParam.bw,testParam.varBw)
            #     newBw = generateBw('square', testParam.linkParams[linkName].bw, testParam.linkParams[linkName].varBw)
            #     for intf in (s2.connectionsTo(pep)[0] + s2.connectionsTo(h2)[0]):
            #         config(intf, bw=newBw)
            #     if testParam.linkParams['pep_h2'].varMethod == 'squareHighPulse':
            #         TbThread.sleep(5)
            #     else:
            #         TbThread.sleep(testParam.linkParams['pep_h2'].varIntv)

            #     # newBw = generateBw('random',testParam.bw,testParam.varBw)
            #     newBw = generateBw('square', testParam.linkParams['pep_h2'].bw, testParam.linkParams['pep-h2'].varBw)
            #     for intf in (s2.connectionsTo(pep)[0] + s2.connectionsTo(h2)[0]):
            #         config(intf, bw=newBw)
            #     if testParam.linkParams['pep_h2'].varMethod == 'squareHighPulse':
            #         TbThread.sleep(testParam.linkParams['pep_h2'].varIntv)
            #     else:
            #         TbThread.sleep(5)
            # else:
            lp = testParam.linksParam.getLP(linkName)
            newBw = generateBw(lp.varMethod, lp.bw, lp.varBw)
            for intf in (nodeA.connectionsTo(switch)[0]+
                    switch.connectionsTo(nodeA)[0]+
                    switch.connectionsTo(nodeB)[0]+
                    nodeB.connectionsTo(switch)[0]):
                config(intf,bw=newBw)
        # linkName is the name of last link in linkNames
         #TODO what if the links have different varIntv
        #sleepWithCaution(testParam.linksParam.defaultLP.varIntv)
        sleepWithCaution(sleeptime)


@threadFunc(False)
def MakeItm(mn, testParam, logPath):
    linkNames = []
    for ln in testParam.topoParam.linkNames():
        if testParam.linksParam.getLP(ln).itmDown>0:
            linkNames.append(ln)
    if linkNames == []:
        return
    
    #TODO what if the links have different itmTotal/itmDown
    anyLP = testParam.linksParam.getLP(linkNames[-1])
    while latchRunning():
        #print("aaaaaaa")
        sleepWithCaution(anyLP.itmTotal-anyLP.itmDown)
        #print("down")
        for l in linkNames:
            nameA,nameB = l.split(Param.LinkNameSep)
            atomic(mn.getNodeByName(nameA).cmd)('echo')
            atomic(mn.configLinkStatus)(nameA,l,'down')
            atomic(mn.getNodeByName(nameB).cmd)('echo')
            atomic(mn.configLinkStatus)(nameB,l,'down')
        sleepWithCaution(anyLP.itmDown)
        #print("up")
        for l in linkNames:
            nameA,nameB = l.split(Param.LinkNameSep)
            atomic(mn.getNodeByName(nameA).cmd)('echo')
            atomic(mn.configLinkStatus)(nameA,l,'up')
            atomic(mn.getNodeByName(nameB).cmd)('echo')
            atomic(mn.configLinkStatus)(nameB,l,'up')
            routeReset(mn,testParam)
    
            
            # if changing s2 - h2
            # mn.getNodeByName('h2').cmd('route add default gw 10.0.2.90 &')
