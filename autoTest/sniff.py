#!/usr/bin/python3

import sys
import os
sys.path.append(os.path.dirname(os.sys.path[0]))
from scapy.all import *
from appLayer.tcpApp import Utils

def Callback(packet):
    #TCP packet
    try:
        if not packet[IP].proto==6:
            return
        length = len(packet[TCP].payload.original)
        print('seq',packet[TCP].seq,'length',length,'time',Utils.getStrTime())
    except:
        return

sniff(filter='src host 10.0.1.1', prn=Callback)
