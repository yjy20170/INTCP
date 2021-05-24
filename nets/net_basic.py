from mininet.link import TCLink


def setTopo(topo, args={}):
    h1 = topo.addHost("h1", ip='10.0.1.1/24')
    s1 = topo.addSwitch("s1")
    h2 = topo.addHost("h2", ip='10.0.1.2/24')

    topo.addLink(h1, s1, cls=TCLink, bw=100, delay="100ms", loss=1)
    topo.addLink(s1, h2, cls=TCLink, bw=100, delay="100ms", loss=1)


def execCmd(mn, args={}):
    h1 = mn.getNodeByName("h1")
    h2 = mn.getNodeByName("h2")
    h1.cmd("route add default gw 10.0.1.1")
    h2.cmd("route add default gw 10.0.1.2")

