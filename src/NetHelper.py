#coding=utf-8

import threading
import thread
import time
import argparse
import importlib
import os

from mininet.cli import CLI

class Args:
    
    def __init__(self,basicArgs=None,dictArgs={},**kwargs):
        if basicArgs != None:
            for key in basicArgs.__dict__:
                if key=='confName':
                    continue
                self.__dict__[key]=basicArgs.__dict__[key]
        if dictArgs != {}:
            for key in dictArgs:
                self.__dict__[key]=dictArgs[key]
        for key in kwargs:
            self.__dict__[key]=kwargs[key]
            
        if 'confName' not in self.__dict__:
            self.confName = self.getConfName()
            
    def getConfName(self):
        return 'bw_'+str(self.bw)+'_rtt_'+str(self.rtt)+'_loss_'+str(self.loss)+'_itm_'+str(self.prdItm)+'_pepcc_'+self.pepcc
    
    @classmethod
    def getArgsFromCli(cls):
        parser = argparse.ArgumentParser()
        parser.add_argument('-net',type=str,default='0')
        parser.add_argument('-bw',type=int,default=-1)
        parser.add_argument('--itm', action='store_const', const=True, default=False, help='add intermittent')
        argsCli = parser.parse_args()
        #TODO
        #args = cls(xxx=argsCli.xxx)
        return args
        
        
def clear():
    os.system("mn -c >/dev/null 2>&1")
    os.system("killall -9 xterm >/dev/null 2>&1")
    # os.system("killall -9 runmn >/dev/null 2>&1")

def importNet(name):
    return importlib.import_module( 'nets.net_'+ name)
    
    
def mngo(args):

    clear()
    # import specified net topo as a module
    myModule = importNet(args.netname)
    # create a new Mininet object
    mn = myModule.createNet(args)
    # start it
    mn.start()
    # execute commands to further configure the network
    myModule.onNetCreated(mn,args)
    
    # start the threads we want to run
    threadLock = threading.Lock()
    threadLock.acquire()
    for th in args.threads:
        thread.start_new_thread( th, (mn,args,threadLock,) )
    # wait until any thread release the lock
    threadLock.acquire()
    
    # terminate
    clear()
    
    
if __name__=="__main__":
    # get args from shell input instead of function input
    args = Args.getArgsFromCli()
    mngo(args)
