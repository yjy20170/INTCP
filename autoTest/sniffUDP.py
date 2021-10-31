#!/usr/bin/python3

import sys
import os
sys.path.append(os.path.dirname(os.sys.path[0]))
from scapy.all import *
from appLayer.tcpApp import Utils

def unpack(bytePayload):
    cmd = int.from_bytes(bytePayload[0:1],byteorder='little')
    wnd = int.from_bytes(bytePayload[1:3],byteorder='little')
    ts = int.from_bytes(bytePayload[3:7],byteorder='little')
    sn = int.from_bytes(bytePayload[7:11],byteorder='little')
    length = int.from_bytes(bytePayload[11:15],byteorder='little')
    rangeStart = int.from_bytes(bytePayload[15:19],byteorder='little')
    rangeEnd = int.from_bytes(bytePayload[19:23],byteorder='little')
    return  cmd,wnd,ts,sn,length,rangeStart,rangeEnd
    
def Callback(packet):
    try:
        #udp packet
        if not packet[IP].proto==17:
            return
        bytePayload =packet.payload.payload.payload.original
        cmd,wnd,ts,sn,length,rangeStart,rangeEnd = unpack(bytePayload)
        #data
        if not cmd==81:
            return
        print("sn",sn,"length",length,"rangeStart",rangeStart,"rangEnd",rangeEnd,"time",Utils.getStrTime())
        #print("sn",sn,"length",length,"rangeStart",rangeStart,"rangEnd",rangeEnd,"time",Utils.getStrTime(),"udplength",len(bytePayload),"ts",ts)
        #print('src:%s----->dst:%s  %s'%(packet[IP].src,packet[IP].dst,str(packet.payload.payload.payload)))
        
    except:
        return


sniff(filter='dst host 10.0.1.1', prn=Callback)
