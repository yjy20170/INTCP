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

#start in the pos
def unpack(bytePayload,pos):
    cmd = int.from_bytes(bytePayload[pos:pos+1],byteorder='little')
    wnd = int.from_bytes(bytePayload[pos+1:pos+3],byteorder='little')
    ts = int.from_bytes(bytePayload[pos+3:pos+7],byteorder='little')
    sn = int.from_bytes(bytePayload[pos+7:pos+11],byteorder='little')
    length = int.from_bytes(bytePayload[pos+11:pos+15],byteorder='little')
    rangeStart = int.from_bytes(bytePayload[pos+15:pos+19],byteorder='little')
    rangeEnd = int.from_bytes(bytePayload[pos+19:pos+23],byteorder='little')
    return  cmd,wnd,ts,sn,length,rangeStart,rangeEnd
    
def Callback_udp(packet):
    try:
        #udp packet
        if not packet[IP].proto==17:
            return
        bytePayload =packet.payload.payload.payload.original
        udpLength = len(bytePayload)
        pos = 0
        while True:
            if pos+23>udpLength:
                break
            cmd,wnd,ts,sn,length,rangeStart,rangeEnd = unpack(bytePayload,pos)
            pos += (23+length)
            # if cmd==81: #data only
                # print("sn",sn,"length",length,"rangeStart",rangeStart,"rangeEnd",rangeEnd,"time",Utils.getStrTime())
            if cmd==86:
                print("time - ts",(int(time.time()*1000)-1636382539776) - ts)
    except:
        return


def Callback_tcp(packet):
    #TCP packet
    try:
        if not packet[IP].proto==6:
            return
        length = len(packet[TCP].payload.original)
        print('seq',packet[TCP].seq,'length',length,'time',Utils.getStrTime())
        #print(packet[IP].src,":",packet[TCP].sport,'-->',packet[IP].dst,":",packet[TCP].dport)
    except:
        return 

if __name__=="__main__":
    print('begin to catch packets..',flush=True)
    args = getArgsFromCli()
    if args.t:
        sniff(filter='src host 10.0.1.1', prn=Callback_tcp) #tcp packet from client to server
    else:
        sniff(filter='dst host 10.0.1.1', prn=Callback_udp) #udp packet from server to client
