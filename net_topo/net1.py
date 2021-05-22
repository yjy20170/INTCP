#!/usr/bin/python

import argparse

from threading import Thread
from subprocess import Popen
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink

class MyTopo(Topo):
    def __init__(self):
        Topo.__init__(self)
        h1 = self.addHost("h1",ip='10.0.1.1/24')
        pep1 = self.addHost("pep1",ip='10.0.1.90/24')
        sat = self.addHost("sat",ip='10.0.3.90/24')
        pep2 = self.addHost("pep2",ip='10.0.4.1/24')
        h2 = self.addHost("h2",ip='10.0.2.1/24')
        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")
        s3 = self.addSwitch("s3")
        s4 = self.addSwitch("s4")
        
        if args.bw <= 0:
            pass
        else:
            self.addLink(h1,s1,cls=TCLink,bw=args.bw)
            self.addLink(s1,pep1,cls=TCLink,bw=args.bw)
            self.addLink(pep1,s3,cls=TCLink,bw=args.bw)
            self.addLink(s3,sat,cls=TCLink,bw=args.bw)
            self.addLink(sat,s4,cls=TCLink,bw=args.bw)
            self.addLink(s4,pep2,cls=TCLink,bw=args.bw)
            self.addLink(pep2,s2,cls=TCLink,bw=args.bw)
            self.addLink(s2,h2,cls=TCLink,bw=args.bw)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-bw',type=int,default=-1)
    args = parser.parse_args()
    
    mn = Mininet(topo=MyTopo())#,xterms=True)
    mn.start()
    pep1 = mn.getNodeByName("pep1")
    pep2 = mn.getNodeByName("pep2")
    h1 = mn.getNodeByName("h1")
    h2 = mn.getNodeByName("h2")
    sat = mn.getNodeByName("sat")
    
    ### for those nodes which connects to n>=2 networks, add n-1 ip here
    
    pep1.cmd("ifconfig pep1-eth1 10.0.3.1 netmask 255.255.255.0")
    
    sat.cmd("ifconfig st-eth1 10.0.4.90 netmask 255.255.255.0")
    
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
    
    mn.interact() 

