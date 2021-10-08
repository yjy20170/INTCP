from mininet.topo import Topo
from mininet.link import TCLink
from mininet.net import Mininet

from testbed.TbNode import TbNode


#TODO automatic; provide IP to application
def splitLoss(loss,n):
    return 100*(1-(1-loss/100)**(1/n))
    
def createNet(testParam):
    topo=Topo()

    #TODO only suitable for chain topo with less than 100 nodes
    # nodes = testParam.absTopoParam.nodes
    # topo.addHost(nodes[0], cls=TbNode)
    # for i in range(1,len(nodes)):
    #     topo.addHost(nodes[i], cls=TbNode)
    #     topo.addSwitch(nodes[i-1]+'-'+nodes[i])
    if testParam.absTopoParam.name=="net_hmmh":

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
                bw = testParam.linkParams['h1-pep1'].bw, delay = '%dms'%(testParam.linkParams['h1-pep1'].rtt/4), loss = splitLoss(testParam.linkParams['h1-pep1'].loss,2))
        topo.addLink(pep1,s1, intfName1 = 'pep1-h1', cls = TCLink, 
                params1 = {'ip':'10.0.1.2/24'},
                bw = testParam.linkParams['h1-pep1'].bw, delay = '%dms'%(testParam.linkParams['h1-pep1'].rtt/4), loss = splitLoss(testParam.linkParams['h1-pep1'].loss,2))

        topo.addLink(pep1,s2, intfName1 = 'pep1-pep2', cls = TCLink, 
                params1 = {'ip':'10.0.3.1/24'},
                bw = testParam.linkParams['pep1-pep2'].bw, delay = '%dms'%(testParam.linkParams['pep1-pep2'].rtt/4), loss = splitLoss(testParam.linkParams['pep1-pep2'].loss,2))
        topo.addLink(pep2,s2, intfName1 = 'pep2-pep1', cls = TCLink, 
                params1 = {'ip':'10.0.3.2/24'},
                bw = testParam.linkParams['pep1-pep2'].bw, delay = '%dms'%(testParam.linkParams['pep1-pep2'].rtt/4), loss = splitLoss(testParam.linkParams['pep1-pep2'].loss,2))

        topo.addLink(pep2,s3, intfName1 = 'pep2-h2', cls = TCLink, 
                params1 = {'ip':'10.0.2.2/24'},
                bw = testParam.linkParams['pep2-h2'].bw, delay = '%dms'%(testParam.linkParams['pep2-h2'].rtt/4), loss = splitLoss(testParam.linkParams['pep2-h2'].loss,2))
        topo.addLink(h2,s3, intfName1 = 'h2-pep2', cls = TCLink, 
                params1 = {'ip':'10.0.2.1/24'},
                bw = testParam.linkParams['pep2-h2'].bw, delay = '%dms'%(testParam.linkParams['pep2-h2'].rtt/4), loss = splitLoss(testParam.linkParams['pep2-h2'].loss,2))

        mn = Mininet(topo)
        mn.start()
    
        # add route rules
        mn.getNodeByName(h1).cmd('route add default gw 10.0.1.2')
        mn.getNodeByName(pep1).cmd('route add default gw 10.0.3.2')
        mn.getNodeByName(pep2).cmd('route add default gw 10.0.2.1')
        mn.getNodeByName(pep2).cmd('route add -net 10.0.1.0 netmask 255.255.255.0 gw 10.0.3.1')
        # mn.getNodeByName(pep2).cmd('route add -net 10.0.2.0 netmask 255.255.255.0 gw 10.0.2.1')
        mn.getNodeByName(h2).cmd('route add default gw 10.0.2.2')
        
        # sat.cmd('route add -net 10.0.1.0 netmask 255.255.255.0 gw 10.0.3.1')
        # sat.cmd('route add default gw 10.0.4.1')
        
        # pep2.cmd('route add default gw 10.0.4.90')
        

        # h2.cmd('route add default gw 10.0.2.90')

    elif testParam.absTopoParam.name=="net_hmh":
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
            #print("---delay---%d"%delay)
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
    

