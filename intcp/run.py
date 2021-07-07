#!/usr/bin/python3

import sys
import importlib
import os
import argparse

from mininet.cli import CLI

import NetParam
from MultiThread import Thread

def getArgsFromCli():
    parser = argparse.ArgumentParser()
    #parser.add_argument('-net',type=str,default='0')
    #parser.add_argument('-bw',type=int,default=-1)
    #parser.add_argument('--itm', action='store_const', const=True, default=False, help='add intermittent')
    parser.add_argument('--m', action='store_const', const=True, default=False, help='enter command line interface(run auto experiment by default)')
    args = parser.parse_args()
    return args
    
def mngo(netParam,isManual, logPath):
    print('initialize network: %s'%netParam.str())

    os.system('mn -c >/dev/null 2>&1')
    os.system('killall -9 xterm >/dev/null 2>&1')
    # os.system('killall -9 runmn >/dev/null 2>&1')

    # import specified net topo as a module
    myModule = importlib.import_module( 'nets.net_%s'%netParam.netName)
    # create a new Mininet object
    mn = myModule.createNet(netParam)
    # start it
    mn.start()

    # execute commands to further configure the network
    # myModule.onNetCreated(mn,netParam)

    # start the threads we want to run
    threads = []
    for func in netParam.funcs:
        threads.append(Thread(func, (mn,netParam,logPath,)))
        threads[-1].start()
    if isManual:
        # enter command line interface...
        CLI(mn)
    else:
        releaserThread = Thread(netParam.releaserFunc, (mn,netParam,logPath,))
        releaserThread.start()
        # main thread waits releaserThread until it ends
        releaserThread.waitToStop()
        for thread in threads:
            thread.join()
        # terminate
        mn.stop()
        return
    
if __name__=='__main__':
    npsetName = 'mot_bwVar_1'
    #npsetName = '06.22.09'#'6.18.14'
    netParams = NetParam.getNetParams(npsetName)
    os.chdir(sys.path[0])
    logRootPath = '../logs'
    if not os.path.exists(logRootPath):
        os.makedirs(logRootPath, mode=0o0777)
    logPath = '%s/%s' % (logRootPath,npsetName)
    if not os.path.exists(logPath):
        os.makedirs(logPath, mode=0o0777)

    isManual = getArgsFromCli().m
    if isManual:
        netParams = netParams[0:1]
    for i,netParam in enumerate(netParams):
        print('Start NetParam %d/%d' % (i+1,len(netParams)))
        mngo(netParam, isManual, logPath)
        
    print('all experiments finished')

    import autoAnlz
    autoAnlz.anlz(npsetName)
    os.system('killall -9 run.py >/dev/null 2>&1')
