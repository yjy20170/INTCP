from mininet.topo import Topo
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.log import info

from testbed.TbNode import TbNode
from testbed import Param
#from TbNode import TbNode
#import Param

def splitLoss(loss,n):
    return 100*(1-(1-loss/100)**(1/n))

#n is midnode number
def gen_linear_topo(n):
	name = "%d_mid"%(n)
	numMidNode = n
	nodes = ['h1']+['m%d'%(i+1) for i in range(n)]+['h2']
	links = [[nodes[i],nodes[i+1]] for i in range(n+1)]
	return TopoParam(name=name,numMidNode=numMidNode,nodes=nodes,links=links)
    
#TODO automatic; provide IP to application
def createNet(testParam):
    topo=Topo()

    #NOTE only suitable for chain topo
    nodes = testParam.topoParam.nodes
    topo.addHost(nodes[0], cls=TbNode)
    for i in range(1,len(nodes)):
        topo.addHost(nodes[i], cls=TbNode)
        linkName = nodes[i-1]+Param.LinkNameSep+nodes[i]
        linkNameRvs = nodes[i]+Param.LinkNameSep+nodes[i-1]
        topo.addSwitch(linkName)

        lp = testParam.linksParam.getLP(linkName)
        delay = lp.rtt/4
        loss = splitLoss(lp.loss,2)
        bw = lp.bw
        if i == len(nodes)-1:
            seg = 100
        else:
            seg = i
        topo.addLink(nodes[i-1],linkName, intfName1 = linkName, cls = TCLink, 
                params1 = {'ip':'10.0.%d.1/24'%seg},
                bw = bw, delay = '%dms'%delay, loss = loss)
        topo.addLink(nodes[i],linkName, intfName1 = linkNameRvs, cls = TCLink, 
                params1 = {'ip':'10.0.%d.2/24'%seg},
                bw = bw, delay = '%dms'%delay, loss = loss)
    mn = Mininet(topo)
    mn.start()
    
    # add route rules
    for i in range(len(nodes)-1):
        if i == len(nodes)-2:
            seg = 100
        else:
            seg = i+1
        mn.getNodeByName(nodes[i]).cmd('route add default gw 10.0.%d.2'%seg)
    mn.getNodeByName(nodes[-1]).cmd('route add default gw 10.0.%d.1'%100)
    for i in range(2,len(nodes)-1):
        for seg in range(1,i):
            mn.getNodeByName(nodes[i]).cmd(
                    'route add -net 10.0.%d.0 netmask 255.255.255.0 gw 10.0.%d.1'%(seg,i))
    mn.getNodeByName(nodes[-1]).cmd('ethtool -K %s_%s tso off'%(nodes[-1],nodes[-2]))
    #BUG bug in Mininet
    # there must be some traffic between the endpoints before running intcp, 
    # otherwise the first dozens of interests will be out of order,
    # leading to severe fake interest hole
    # so we use ping here
    mn.ping([mn['h1'],mn['h2']],outputer=info)

    return mn
def gen_test_trace(): # only for test, the first second 
    max_midnodes = 16
    total_midnodes = 16
    isls = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),
            (8,9),(9,10),(10,11),(11,12),(12,13),(13,14),(14,15),(15,16),(16,-1)]
    #links_params = None
    link_param_1 = {"topo":[(i+1) for i in range(16)],
                    "rtt":[50,6.43,13.08,13.08,8.96,4.15,8.96,4.15,8.96,4.15,
                            8.96,4.15,8.96,4.15,8.96,13.08,13.08,4.33,50],
                    #"rtt":[50]+[10]*18+[50],
                    "loss":[0]+[0]*17+[0],
                    "bw":[20]*17+[5,20]}
    links_params = [link_param_1]
    return max_midnodes,total_midnodes,isls,links_params

def gen_extreme_trace(): #extreme topo ,when link change per 1s can beat bbr
    max_midnodes = 6
    total_midnodes = 12
    isls = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,-1),
            (0,7),(7,8),(8,9),(9,10),(10,11),(11,12),(12,-1)]
    #links_params = None
    link_param_1 = {"topo":[1,2,3,4,5,6],"rtt":[20,10,10,10,10,10,10,10,20],"loss":[0,1,1,1,1,1,1,1,0],"bw":[20,20,20,20,20,20,20,20,20]}
    link_param_2 = {"topo":[7,8,9,10,11,12],"rtt":[20,10,20,20,20,20,20,10,20],"loss":[0,1,1,1,1,1,1,1,0],"bw":[20,20,20,20,20,20,20,20,20]}
    links_params = [link_param_2]+[link_param_1]
    return max_midnodes,total_midnodes,isls,links_params

def gen_link_change_trace():
    max_midnodes = 2
    total_midnodes = 4
    isls = [(0,1),(1,2),(2,-1),(0,3),(3,4),(4,-1),(3,2)]
    #links_params = None
    link_param_1 = {"topo":[1,2],"rtt":[20,10,20,10,20],"loss":[0,0.1,0.1,0.1,0],"bw":[20,20,20,20,20]}
    link_param_2 = {"topo":[3,4],"rtt":[20,10,10,10,20],"loss":[0,0.1,0.1,0.1,0],"bw":[20,20,20,20,20]}
    links_params = [link_param_1,link_param_2]
    return max_midnodes,total_midnodes,isls,links_params

def setRoute_old(mn,isls,topo):
    segs = []
    segs.append(1)  #h1-gs1
    segs.append(isls.index((0,topo[0]))+2)
    for i in range(len(topo)-1):
        segs.append(isls.index((topo[i],topo[i+1]))+2)
    segs.append(isls.index((topo[-1],-1))+2)
    segs.append(100) #gs1-h2

    nodes = ['h1','gs1']+['m%d'%(topo[i]) for i in range(len(topo))]+['gs2','h2']

    #set default gw
    for i in range(len(nodes)-1):
        #mn.getNodeByName(nodes[i]).cmd('route del default')
        mn.getNodeByName(nodes[i]).cmd('route add default gw 10.0.%d.2'%(segs[i]))
    #mn.getNodeByName(nodes[-1]).cmd('route del default')
    mn.getNodeByName(nodes[-1]).cmd('route add default gw 10.0.%d.1'%(segs[-1]))

    #set other gw
    for i in range(2,len(nodes)-1):
        for j in range(i-1):
            mn.getNodeByName(nodes[i]).cmd('route add -net 10.0.%d.0 netmask 255.255.255.0 gw 10.0.%d.1'%(segs[j],segs[i-1]))
        #mn.getNodeByName(nodes[i]).cmd('route add -net 10.0.%d.0 netmask 255.255.255.0 gw 10.0.%d.1'%(1,segs[i-1]))
    #ping h1 h2

def setRoute(mn,isls,topo):
    if topo is None:
        return
    segs = []
    segs.append((1,1))  # the first 1 means seg ,the sencond 1 means seg.1 is left
    segs.append((isls.index((0,topo[0]))+2,1))
    for i in range(len(topo)-1):
        if (topo[i],topo[i+1]) in isls:
            segs.append((isls.index((topo[i],topo[i+1]))+2,1))
        else:
            segs.append((isls.index((topo[i+1],topo[i]))+2,2))
    segs.append((isls.index((topo[-1],-1))+2,1))
    segs.append((100,1))
    nodes = ['h1','gs1']+['m%d'%(topo[i]) for i in range(len(topo))]+['gs2','h2']
    #print(nodes)

    #delete default gw
    for i in range(len(nodes)-1):
        mn.getNodeByName(nodes[i]).cmd('route add default gw 10.0.%d.%d'%(segs[i][0],3-segs[i][1]))
    mn.getNodeByName(nodes[-1]).cmd('route add default gw 10.0.%d.%d'%(segs[-1][0],segs[-1][1]))

    #delete other gw
    for i in range(2,len(nodes)-1):
        for j in range(i-1):
            mn.getNodeByName(nodes[i]).cmd('route add -net 10.0.%d.0 netmask 255.255.255.0 gw 10.0.%d.%d'%(segs[j][0],segs[i-1][0],segs[i-1][1]))

#clear route for previous topo
def clearRoute_old(mn,isls,topo):
    if topo is None:
        return
    segs = []
    segs.append(1)
    segs.append(isls.index((0,topo[0]))+2)
    for i in range(len(topo)-1):
        segs.append(isls.index((topo[i],topo[i+1]))+2)
    segs.append(isls.index((topo[-1],-1))+2)
    segs.append(100)
    nodes = ['h1','gs1']+['m%d'%(topo[i]) for i in range(len(topo))]+['gs2','h2']
    #print(nodes)

    #delete default gw
    for i in range(len(nodes)-1):
        mn.getNodeByName(nodes[i]).cmd('route del default gw 10.0.%d.2'%(segs[i]))
    mn.getNodeByName(nodes[-1]).cmd('route del default gw 10.0.%d.1'%(segs[-1]))

    #delete other gw
    for i in range(2,len(nodes)-1):
        for j in range(i-1):
            mn.getNodeByName(nodes[i]).cmd('route del -net 10.0.%d.0 netmask 255.255.255.0 gw 10.0.%d.1'%(segs[j],segs[i-1]))
        #mn.getNodeByName(nodes[i]).cmd('route del -net 10.0.%d.0 netmask 255.255.255.0 gw 10.0.%d.1'%(1,segs[i-1]))
    #ping h1 h2

def clearRoute(mn,isls,topo):
    if topo is None:
        return
    segs = []
    segs.append((1,1))  # the first 1 means seg ,the sencond 1 means seg.1 is left
    segs.append((isls.index((0,topo[0]))+2,1))
    for i in range(len(topo)-1):
        if (topo[i],topo[i+1]) in isls:
            segs.append((isls.index((topo[i],topo[i+1]))+2,1))
        else:
            segs.append((isls.index((topo[i+1],topo[i]))+2,2))
    segs.append((isls.index((topo[-1],-1))+2,1))
    segs.append((100,1))
    nodes = ['h1','gs1']+['m%d'%(topo[i]) for i in range(len(topo))]+['gs2','h2']
    #print(nodes)

    #delete default gw
    for i in range(len(nodes)-1):
        mn.getNodeByName(nodes[i]).cmd('route del default gw 10.0.%d.%d'%(segs[i][0],3-segs[i][1]))
    mn.getNodeByName(nodes[-1]).cmd('route del default gw 10.0.%d.%d'%(segs[-1][0],segs[-1][1]))

    #delete other gw
    for i in range(2,len(nodes)-1):
        for j in range(i-1):
            mn.getNodeByName(nodes[i]).cmd('route del -net 10.0.%d.0 netmask 255.255.255.0 gw 10.0.%d.%d'%(segs[j][0],segs[i-1][0],segs[i-1][1]))

# create net for dynamic topo
# h1-gs1-isls-gs2-h2, 
def create_dynamic_net(dynamic_topo):
    if dynamic_topo is None:
        dynamic_topo = gen_simple_trace()
    max_midnodes,total_midnodes,isls,links_params = dynamic_topo
    topo = Topo()

    #create nodes
    nodes = ['h1','h2','gs1','gs2'] + ['m%d'%(i+1) for i in range(total_midnodes)] 
    for i in range(len(nodes)):
        topo.addHost(nodes[i], cls=TbNode)
    
    #create links and set ip
    create_all_links(topo,isls)
    
    #set initial route
    mn = Mininet(topo)
    mn.start()
    
    mn.getNodeByName(nodes[-1]).cmd('ethtool -K %s_%s tso off'%('h2','gs2'))
    mn.ping([mn['h1'],mn['h2']],outputer=info)

    #setRoute(mn,isls,[1,2])
    #setRoute(mn,isls,[3,4])
    #mn.enterCli()
    return mn

def create_test_net():
    topo = Topo()
    topo.addHost('h1',cls=TbNode)
    for i in range(2,10):
        node_name = 'h%d'%(i)
        topo.addHost(node_name,cls=TbNode)
        linkName = 'h1' +'_'+ node_name
        linkNameRvs = node_name+'_'+'h1'
        topo.addSwitch(linkName)
        topo.addLink('h1',linkName, intfName1 = linkName, cls = TCLink, 
                params1 = {'ip':'10.0.%d.1/24'%i})
        topo.addLink(node_name,linkName, intfName1 = linkNameRvs, cls = TCLink, 
                params1 = {'ip':'10.0.%d.2/24'%i})
    mn = Mininet(topo)
    mn.start()
    mn.enterCli()
    return

# 10.0.1.1 reserve for h1, 10.0.100.2 reserve for h2
# in isls, 0 represent gs1 and -1 represent for gs2 
def create_all_links(topo,isls,bw=10,delay=10,loss=0):
    #TODO
    for i,isl in enumerate(isls):
        numA,numB = isl
        nameA = 'gs1' if numA==0 else 'm%d'%(numA)
        nameB = 'gs2' if numB==-1 else 'm%d'%(numB)
        linkName = nameA + Param.LinkNameSep + nameB
        linkNameRvs = nameB + Param.LinkNameSep+ nameA
        topo.addSwitch(linkName)
        topo.addLink(nameA,linkName, intfName1 = linkName, cls = TCLink, 
                params1 = {'ip':'10.0.%d.1/24'%(i+2)},bw = bw,delay=delay,loss=loss)
        topo.addLink(nameB,linkName, intfName1 = linkNameRvs, cls = TCLink, 
                params1 = {'ip':'10.0.%d.2/24'%(i+2)},bw = bw,delay=delay,loss=loss)

    #set ground link h1-gs1 and h2-gs2
    topo.addSwitch('h1_gs1')
    topo.addSwitch('gs2_h2')
    topo.addLink('h1','h1_gs1', intfName1 = 'h1_gs1', cls = TCLink, 
                params1 = {'ip':'10.0.1.1/24'},bw=bw,delay=delay,loss=loss)
    topo.addLink('gs1','h1_gs1', intfName1 = 'gs1_h1', cls = TCLink, 
                params1 = {'ip':'10.0.1.2/24'},bw=bw,delay=delay,loss=loss)
    topo.addLink('gs2','gs2_h2', intfName1 = 'gs2_h2', cls = TCLink, 
                params1 = {'ip':'10.0.100.1/24'},bw=bw,delay=delay,loss=loss)
    topo.addLink('h2','gs2_h2', intfName1 = 'h2_gs2', cls = TCLink, 
                params1 = {'ip':'10.0.100.2/24'},bw=bw,delay=delay,loss=loss)      
    #initialize all links

def createNet_deprecated(testParam):
    topo=Topo()
    if testParam.topoParam.name=="net_hmmh":

        h1 = topo.addHost('h1', cls=TbNode)
        s1 = topo.addSwitch('h1-pep1')
        pep1 = topo.addHost('pep1', cls=TbNode)
        s2 = topo.addSwitch('pep1-pep2')
        pep2 = topo.addHost('pep2', cls=TbNode)
        s3 = topo.addSwitch('pep2-h2')
        h2 = topo.addHost('h2', cls=TbNode)
        
        delay = 0
        loss = 0
        bw = 100
        topo.addLink(h1,s1, intfName1 = 'h1-pep1', cls = TCLink, 
                params1 = {'ip':'10.0.1.1/24'},
                bw = bw, delay = '%dms'%delay, loss = loss)
        topo.addLink(pep1,s1, intfName1 = 'pep1-h1', cls = TCLink, 
                params1 = {'ip':'10.0.1.2/24'},
                bw = bw, delay = '%dms'%delay, loss = loss)

        topo.addLink(pep1,s2, intfName1 = 'pep1-pep2', cls = TCLink, 
                params1 = {'ip':'10.0.2.1/24'},
                bw = bw, delay = '%dms'%delay, loss = loss)
        topo.addLink(pep2,s2, intfName1 = 'pep2-pep1', cls = TCLink, 
                params1 = {'ip':'10.0.2.2/24'},
                bw = bw, delay = '%dms'%delay, loss = loss)

        topo.addLink(pep2,s3, intfName1 = 'pep2-h1', cls = TCLink, 
                params1 = {'ip':'10.0.100.1/24'},
                bw = bw, delay = '%dms'%delay, loss = loss)
        topo.addLink(h2,s3, intfName1 = 'h2-pep2', cls = TCLink, 
                params1 = {'ip':'10.0.100.2/24'},
                bw = bw, delay = '%dms'%delay, loss = loss)
        mn = Mininet(topo)
        mn.start()
    
        # add route rules
        mn.getNodeByName(h1).cmd('route add default gw 10.0.1.2')
        mn.getNodeByName(pep1).cmd('route add default gw 10.0.2.2')
        mn.getNodeByName(pep2).cmd('route add default gw 10.0.100.2')
        mn.getNodeByName(pep2).cmd('route add -net 10.0.1.0 netmask 255.255.255.0 gw 10.0.2.1')
        # mn.getNodeByName(pep2).cmd('route add -net 10.0.2.0 netmask 255.255.255.0 gw 10.0.2.1')
        mn.getNodeByName(h2).cmd('route add default gw 10.0.100.1')
        
        # sat.cmd('route add -net 10.0.1.0 netmask 255.255.255.0 gw 10.0.3.1')
        # sat.cmd('route add default gw 10.0.4.1')
        
        # pep2.cmd('route add default gw 10.0.4.90')
        
        # h2.cmd('route add default gw 10.0.2.90')
    elif testParam.topoParam.name=="net_hmh":
        router = 'pep'
        topo.addNode(router, cls=TbNode)
        hostsNum = 2
        for hindex in range(1,hostsNum+1):
            if hindex == 1:
                delay = testParam.linkParams['h1-pep'].rtt/4
                loss = testParam.linkParams['h1-pep'].loss
                bw =testParam.linkParams['h1-pep'].bw
            elif hindex == 2:
                delay = testParam.linkParams['pep-h2'].rtt/4
                loss = testParam.linkParams['pep-h2'].loss
                bw =testParam.linkParams['pep-h2'].bw
            else:
                delay = 0
                loss = 0
                bw = 0

            if hindex == 1:
                switch = 'h1-pep'
            else:
                switch = 'pep-h2'
            topo.addSwitch(switch)
            topo.addLink(switch,router,
                        intfName2 = '%s-eth%d' % (router,hindex),
                        params2 = {'ip':'10.0.%d.100/24' % hindex},
                        cls = TCLink, bw = bw, delay = '%dms'%delay, loss = splitLoss(loss,2))
            host = 'h%d' % hindex
            topo.addNode(host, cls=TbNode,
                        ip='10.0.%d.1/24' % hindex,
                        defaultRoute = 'via 10.0.%d.100' % hindex)

            topo.addLink(switch, host,
                        cls = TCLink, bw = bw, delay = '%dms'%delay, loss = splitLoss(loss,2))

        mn = Mininet(topo)
        mn.start()

    return mn

'''
if __name__ =="__main__":
    trace = gen_simple_trace()
    create_dynamic_net(trace)
'''