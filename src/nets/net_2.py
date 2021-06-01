from mininet.topo import Topo
from mininet.link import TCLink
from mininet.net import Mininet

def createNet(args):
    topo=Topo()

    h1 = topo.addHost("h1",ip='10.0.1.1/24')
    h2 = topo.addHost("h2",ip='10.0.2.1/24')
    h3 = topo.addHost("h3",ip='10.0.1.2/24')
    h4 = topo.addHost("h4",ip='10.0.2.2/24')
    pep = topo.addHost("pep",ip='10.0.1.90/24')
    
    s1 = topo.addSwitch("s1")
    s2 = topo.addSwitch("s2")
    
    
    topo.addLink(h1,s1,cls=TCLink,  bw=10, delay=  "0ms")
    topo.addLink(h3,s1,cls=TCLink,  bw=10, delay=  "0ms")
    topo.addLink(s1,pep,cls=TCLink, bw=10, delay=  "12.4ms")
    topo.addLink(pep,s2,cls=TCLink, bw=1000, delay="0ms")
    topo.addLink(s2,h2,cls=TCLink,  bw=10, delay="287.5ms",loss=0.5)
    topo.addLink(s2,h4,cls=TCLink,  bw=10, delay="0ms")
     
    return Mininet(topo)
        
def onNetCreated(mn,args):
    pep = mn.getNodeByName("pep")
    h1 = mn.getNodeByName("h1")
    h2 = mn.getNodeByName("h2")
    h3 = mn.getNodeByName("h3")
    h4 = mn.getNodeByName("h4")
    pep.cmd("ifconfig pep-eth1 10.0.2.90 netmask 255.255.255.0")
    h1.cmd("route add default gw 10.0.1.90")
    h2.cmd("route add default gw 10.0.2.90")
    h3.cmd("route add default gw 10.0.1.90")
    h4.cmd("route add default gw 10.0.2.90")
    pep.cmd("sysctl net.ipv4.ip_forward=1")
    

