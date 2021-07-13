from mininet.topo import Topo
from mininet.link import TCLink
from mininet.net import Mininet

import MyNode

def createNet(args):
    topo=Topo()
    router = 'pep'
    topo.addNode(router, cls=MyNode.PEPNode)
    hostsNum = 2
    for hindex in range(1,hostsNum+1):
        if hindex == 1:
            delay = (args.rttTotal-args.rttSat)/4
            loss = 0
            # TODO
            # Now the bandwidth is hardcoded. Need to change.
            # 10 -> 60
            bw = 60
        elif hindex == 2:
            delay = args.rttSat/4
            loss = args.loss/2
            bw = args.bw
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
        topo.addNode(host, cls=MyNode.EndpointNode,
                     ip='10.0.%d.1/24' % hindex,
                     defaultRoute = 'via 10.0.%d.100' % hindex)

        topo.addLink(switch, host,
                     cls = TCLink, bw = bw, delay = '%dms'%delay, loss = loss)

    return Mininet(topo)





