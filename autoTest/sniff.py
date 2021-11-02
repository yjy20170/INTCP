#!/usr/bin/python3

import sys
import os
import argparse
from scapy.all import *

sys.path.append(os.path.dirname(os.sys.path[0]))
from appLayer.tcpApp import Utils

def getArgsFromCli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--t',action='store_const', const=True, default=False, help='sniffer for tcp packets')
    args = parser.parse_args()
    return args
    
def unpack(bytePayload):
    cmd = int.from_bytes(bytePayload[0:1],byteorder='little')
    wnd = int.from_bytes(bytePayload[1:3],byteorder='little')
    ts = int.from_bytes(bytePayload[3:7],byteorder='little')
    sn = int.from_bytes(bytePayload[7:11],byteorder='little')
    length = int.from_bytes(bytePayload[11:15],byteorder='little')
    rangeStart = int.from_bytes(bytePayload[15:19],byteorder='little')
    rangeEnd = int.from_bytes(bytePayload[19:23],byteorder='little')
    return  cmd,wnd,ts,sn,length,rangeStart,rangeEnd
    
def Callback_udp(packet):
    try:
        #udp packet
        if not packet[IP].proto==17:
            return
        bytePayload =packet.payload.payload.payload.original
        cmd,wnd,ts,sn,length,rangeStart,rangeEnd = unpack(bytePayload)
        #data
        if not cmd==81:
            return
        print("sn",sn,"length",length,"rangeStart",rangeStart,"rangeEnd",rangeEnd,"time",Utils.getStrTime())
        #print("sn",sn,"length",length,"rangeStart",rangeStart,"rangEnd",rangeEnd,"time",Utils.getStrTime(),"udplength",len(bytePayload),"ts",ts)
        #print('src:%s----->dst:%s  %s'%(packet[IP].src,packet[IP].dst,str(packet.payload.payload.payload)))
        
    except:
        return


def Callback_tcp(packet):
    #TCP packet
    try:
        if not packet[IP].proto==6:
            return
        length = len(packet[TCP].payload.original)
        print('seq',packet[TCP].seq,'length',length,'time',Utils.getStrTime())
    except:
        return 

if __name__=="__main__":
    print('begin to catch packets..',flush=True)
    args = getArgsFromCli()
    if args.t:
        sniff(filter='src host 10.0.1.1', prn=Callback_tcp) #tcp packet from client to server
    else:
        sniff(filter='dst host 10.0.1.1', prn=Callback_udp) #udp packet from server to client
