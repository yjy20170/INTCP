import thread
import time
import argparse

import os
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink

class AbsNetwork:
    hosts=[]
    switches=[]
    links=[]
    linkInfos=[]
    mn=None
    args=None

    def __init__(self,hosts=[],switches=[],links=[]):
        self.hosts=hosts
        self.switches=switches
        self.links=links

        
    def loadArgs(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-net',type=str,default='0')
        parser.add_argument('-bw',type=int,default=-1)
        parser.add_argument('--itm', action='store_const', const=True, default=False, help='add intermittent')
        self.args = parser.parse_args()
        
    def startMN(self):
        # clear
        os.system('mn -c >/dev/null 2>&1')
        os.system('killall -9 xterm >/dev/null 2>&1')
        
        topo=Topo()
        # # set topo
        # for node in self.nodes:
        #     if node[0]=='h':

        h1 = topo.addHost("h1",ip='10.0.1.1/24')
        s1 = topo.addSwitch("s1")
        pep = topo.addHost("pep",ip='10.0.1.90/24')
        s2 = topo.addSwitch("s2")
        h2 = topo.addHost("h2",ip='10.0.2.1/24')

        topo.addLink(h1,s1,cls=TCLink,  bw=10, delay=  "0ms")
        topo.addLink(s1,pep,cls=TCLink, bw=10, delay=  "12.4ms")
        topo.addLink(pep,s2,cls=TCLink, bw=1000, delay="0ms")
        topo.addLink(s2,h2,cls=TCLink,  bw=10, delay="287.5ms",loss=0.5)
        #setTopo(topo)
        
        mn = Mininet(topo)
        
        # set topo part II
        pep = mn.getNodeByName("pep")
        h1 = mn.getNodeByName("h1")
        h2 = mn.getNodeByName("h2")
        pep.cmd("ifconfig pep-eth1 10.0.2.90 netmask 255.255.255.0")
        h1.cmd("route add default gw 10.0.1.90")
        h2.cmd("route add default gw 10.0.2.90")
        pep.cmd("sysctl net.ipv4.ip_forward=1")
        
        mn.interact()

first=AbsNetwork(['h1','s1','h2'],[['h1','s1'],['s1','h2']])
first.startMN()
