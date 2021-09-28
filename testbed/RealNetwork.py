from mininet.topo import Topo
from mininet.link import TCLink
from mininet.net import Mininet

from testbed.TbNode import TbNode


#TODO automatic; provide IP to application

def createNet(testParam):
    topo=Topo()

    ###########################
    if testParam.absTopoParam.name=="net_hmmh":
        
        h1 = topo.addHost('h1',ip='10.0.1.1/24')
        pep1 = topo.addHost('pep1',ip='10.0.1.90/24')
        sat = topo.addHost('sat',ip='10.0.3.90/24')
        pep2 = topo.addHost('pep2',ip='10.0.4.1/24')
        h2 = topo.addHost('h2',ip='10.0.2.1/24')
        s1 = topo.addSwitch('s1')
        s2 = topo.addSwitch('s2')
        s3 = topo.addSwitch('s3')
        s4 = topo.addSwitch('s4')
        
        topo.addLink(h1,s1)
        topo.addLink(s1,pep1)
        topo.addLink(pep1,s3)
        topo.addLink(s3,sat)
        topo.addLink(sat,s4)
        topo.addLink(s4,pep2)
        topo.addLink(pep2,s2)
        topo.addLink(s2,h2)
        
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

            switch = 's%d' % hindex
            topo.addSwitch(switch)
            topo.addLink(switch,router,
                        intfName2 = '%s-eth%d' % (router,hindex),
                        params2 = {'ip':'10.0.%d.100/24' % hindex},
                        cls = TCLink, bw = bw, delay = '%dms'%delay, loss = loss)

            host = 'h%d' % hindex
            topo.addNode(host, cls=TbNode,
                        ip='10.0.%d.1/24' % hindex,
                        defaultRoute = 'via 10.0.%d.100' % hindex)

            topo.addLink(switch, host,
                        cls = TCLink, bw = bw, delay = '%dms'%delay, loss = loss)
    ###########################

    mn = Mininet(topo)
    mn.start()
    onNetCreated(mn, testParam)

    return mn
    
# execute commands to further configure the network
def onNetCreated(mn, testParam):
    if testParam.absTopoParam.name=="net_hmmh":
        pep1 = mn.getNodeByName('pep1')
        pep2 = mn.getNodeByName('pep2')
        h1 = mn.getNodeByName('h1')
        h2 = mn.getNodeByName('h2')
        sat = mn.getNodeByName('sat')

        ### for those nodes which connects to n>=2 networks, add n-1 ip here

        pep1.cmd('ifconfig pep1-eth1 10.0.3.1 netmask 255.255.255.0')

        sat.cmd('ifconfig sat-eth1 10.0.4.90 netmask 255.255.255.0')

        pep2.cmd('ifconfig pep2-eth1 10.0.2.90 netmask 255.255.255.0')

        ### how to forward while receiving a packet

        h1.cmd('route add default gw 10.0.1.90')

        pep1.cmd('route add default gw 10.0.3.90')

        sat.cmd('route add -net 10.0.1.0 netmask 255.255.255.0 gw 10.0.3.1')
        sat.cmd('route add default gw 10.0.4.1')

        pep2.cmd('route add default gw 10.0.4.90')

        h2.cmd('route add default gw 10.0.2.90')

        ###

        pep1.cmd('sysctl net.ipv4.ip_forward=1')
        sat.cmd('sysctl net.ipv4.ip_forward=1')
        pep2.cmd('sysctl net.ipv4.ip_forward=1') 
    else:
        return
