from mininet.link import TCLink

def setTopo(topo,args={}):

    h1 = topo.addHost("h1",ip='10.0.1.1/24')
    pep1 = topo.addHost("pep1",ip='10.0.1.90/24')
    sat = topo.addHost("sat",ip='10.0.3.90/24')
    pep2 = topo.addHost("pep2",ip='10.0.4.1/24')
    h2 = topo.addHost("h2",ip='10.0.2.1/24')
    s1 = topo.addSwitch("s1")
    s2 = topo.addSwitch("s2")
    s3 = topo.addSwitch("s3")
    s4 = topo.addSwitch("s4")
    
    topo.addLink(h1,s1)
    topo.addLink(s1,pep1)
    topo.addLink(pep1,s3)
    topo.addLink(s3,sat)
    topo.addLink(sat,s4)
    topo.addLink(s4,pep2)
    topo.addLink(pep2,s2)
    topo.addLink(s2,h2)
        
def execCmd(mn,args={}):
    pep1 = mn.getNodeByName("pep1")
    pep2 = mn.getNodeByName("pep2")
    h1 = mn.getNodeByName("h1")
    h2 = mn.getNodeByName("h2")
    sat = mn.getNodeByName("sat")
    
    ### for those nodes which connects to n>=2 networks, add n-1 ip here
    
    pep1.cmd("ifconfig pep1-eth1 10.0.3.1 netmask 255.255.255.0")
    
    sat.cmd("ifconfig sat-eth1 10.0.4.90 netmask 255.255.255.0")
    
    pep2.cmd("ifconfig pep2-eth1 10.0.2.90 netmask 255.255.255.0")
    
    ### how to forward while receiving a packet
    
    h1.cmd("route add default gw 10.0.1.90")
    
    pep1.cmd("route add default gw 10.0.3.90")
    
    sat.cmd("route add -net 10.0.1.0 netmask 255.255.255.0 gw 10.0.3.1")
    sat.cmd("route add default gw 10.0.4.1")
    
    pep2.cmd("route add default gw 10.0.4.90")
    
    h2.cmd("route add default gw 10.0.2.90")
    
    ###
    
    pep1.cmd("sysctl net.ipv4.ip_forward=1")
    sat.cmd("sysctl net.ipv4.ip_forward=1")
    pep2.cmd("sysctl net.ipv4.ip_forward=1")
    
