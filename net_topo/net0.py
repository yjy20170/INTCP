#!/usr/bin/python

import thread
import time

import argparse


from subprocess import Popen
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink

class MyTopo(Topo):
    def __init__(self):
        Topo.__init__(self)
        h1 = self.addHost("h1",ip='10.0.1.1/24')
        h2 = self.addHost("h2",ip='10.0.2.1/24')
        pep = self.addHost("pep",ip='10.0.1.90/24')
        
        s1 = self.addSwitch("s1")
        s2 = self.addSwitch("s2")
        
        
        self.addLink(h1,s1,cls=TCLink,  bw=10, delay=  "0ms")
        self.addLink(s1,pep,cls=TCLink, bw=10, delay=  "12.4ms")
        self.addLink(pep,s2,cls=TCLink, bw=1000, delay="0ms")
        self.addLink(s2,h2,cls=TCLink,  bw=10, delay="287.5ms",loss=0.5)

        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-bw',type=int,default=-1)
    args = parser.parse_args()
    
    mn = Mininet(topo=MyTopo())#,xterms=True)
    mn.start()
    pep = mn.getNodeByName("pep")
    h1 = mn.getNodeByName("h1")
    h2 = mn.getNodeByName("h2")
    pep.cmd("ifconfig pep-eth1 10.0.2.90 netmask 255.255.255.0")
    h1.cmd("route add default gw 10.0.1.90")
    h2.cmd("route add default gw 10.0.2.90")
    pep.cmd("sysctl net.ipv4.ip_forward=1")
    
    def linkupdown():
       while 1:
          time.sleep(8)
          mn.configLinkStatus('s1','pep','down')
          time.sleep(2)
          mn.configLinkStatus('s1','pep','up')
    def mn_inte(mn):
        mn.interact()
    # create two threads
    # thread.start_new_thread( mn_inte, (mn,) )
    # thread.start_new_thread( linkupdown, () )
    
    mn.interact()

