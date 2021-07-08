import time
import argparse

import os
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink

class AbsNetwork:
    args=None

    def __init__(self,hosts=[],switches=[],links=[]):
        self.hosts=hosts
        self.switches=switches
        self.links=links

        self.hosts = []
        self.switches = []
        self.links = []
        self.linkInfos = []
        self.mn = None
        
    def loadArgs(self):
        pass
        
    def startMN(self):
        pass

first=AbsNetwork(['h1','s1','h2'],[['h1','s1'],['s1','h2']])
first.startMN()
