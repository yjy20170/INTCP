from mininet.topo import Topo
from mininet.link import TCLink
from mininet.net import Mininet

import MyNode

def createNet(args):
    # TODO
    # try to remove switches
    topo = Topo()

    h1 = topo.addNode('h1')#, ip='10.0.0.1/24')
    pep = topo.addHost('pep', cls=MyNode.PEPNode)#, ip='10.0.0.2/24')
    h2 = topo.addHost('h2')#, ip='10.0.1.90/24')

    topo.addLink(h1, pep,
                 intfName1 = 'h1-r',
                 params1 = {'ip': '10.0.1.1/24'},
                 intfName2 = 'pep-l',
                 params2 = {'ip':'10.0.1.2/24'})
    topo.addLink(pep, h2,
                 intfName1 = 'pep-r',
                 params1 = {'ip': '10.0.2.1/24',
                     'defaultRoute':'via 10.0.1.1'},
                 intfName2 = 'h2-l',
                 params2 = {'ip':'10.0.2.2/24'})

    return Mininet(topo)


def onNetCreated(mn, args):
    pep1 = mn.getNodeByName('pep1')
    h1 = mn.getNodeByName('h1')

    ### for those nodes which connects to n>=2 networks, add n-1 ip here


    ### how to forward while receiving a packet

    #h1.cmd('route add default gw 10.0.1.90')

    #pep1.cmd('route add default gw 10.0.3.90')

    ###
