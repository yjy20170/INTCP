#coding=utf-8

import threading
import thread

import importlib
import os

from mininet.cli import CLI

from Args import Args
        
        
def clear():
    os.system("mn -c >/dev/null 2>&1")
    os.system("killall -9 xterm >/dev/null 2>&1")
    # os.system("killall -9 runmn >/dev/null 2>&1")

def importNet(name):
    return importlib.import_module( 'nets.net_'+ name)
    
    
def mngo(args,isAuto):
    print("start experiment with network: "+args.getArgsName())
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
        if not isAuto and th.__name__=="ipfThread":
            continue
        thread.start_new_thread( th, (mn,args,threadLock,) )
    
    if not isAuto:
        CLI(mn)
        return
        
    print('main thread waiting...')
    # wait until any thread release the lock
    threadLock.acquire()
    # terminate
    clear()
    print('terminate experiment\n')
    
    
if __name__=="__main__":
    # get args from shell input instead of function input
    args = Args.getArgsFromCli()
    mngo(args)
