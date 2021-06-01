#coding=utf-8

import thread
import time
import argparse
import importlib

import os

from mininet.cli import CLI


def clear():
    os.system("mn -c >/dev/null 2>&1")
    os.system("killall -9 xterm >/dev/null 2>&1")
    os.system("killall -9 runmn >/dev/null 2>&1")
    
def start(mn,onNetCreated,args={}):
    mn.start()
    onNetCreated(mn,args)
    for th in args.threads:
        thread.start_new_thread( th, (mn,args,) )

    return CLI(mn)
    
def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('-net',type=str,default='0')
    parser.add_argument('-bw',type=int,default=-1)
    parser.add_argument('--itm', action='store_const', const=True, default=False, help='add intermittent')
    args = parser.parse_args()
    return args
    
def importNet(name):
    return importlib.import_module( 'nets.net_'+ name)#,'nets')
    
if __name__=="__main__":
    print(importNet('0'))
class Args:
    def __init__(self,confName,testLen,threads,net,bw,rtt,loss,pepcc):
        self.confName = confName
        self.testLen = testLen
        self.threads = threads
        self.net = net
        self.bw = bw
        self.rtt = rtt
        self.loss = loss
        self.pepcc = pepcc
