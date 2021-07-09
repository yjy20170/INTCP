#!/usr/bin/python3

import sys
import importlib
import os
import argparse

from mininet.cli import CLI

import NetEnv
from MultiThread import Thread,ReleaserThread

import autoAnlz

def getArgsFromCli():
    parser = argparse.ArgumentParser()
    #parser.add_argument('-net',type=str,default='0')
    #parser.add_argument('-bw',type=int,default=-1)
    #parser.add_argument('--itm', action='store_const', const=True, default=False, help='add intermittent')
    parser.add_argument('--m', action='store_const', const=True, default=False, help='enter command line interface(run auto experiment by default)')
    args = parser.parse_args()
    return args
    
def mngo(netEnv, isManual, logPath):
    os.system('mn -c >/dev/null 2>&1')
    os.system('killall -9 xterm >/dev/null 2>&1')
    # os.system('killall -9 runmn >/dev/null 2>&1')

    # import specified net topo as a module
    myModule = importlib.import_module( 'nets.net_%s' % netEnv.netName)
    # create a new Mininet object
    mn = myModule.createNet(netEnv)
    # start it
    mn.start()

    # execute commands to further configure the network
    # myModule.onNetCreated(mn,netEnv)

    # start the threads we want to run
    threads = []
    if isManual:
        for func in netEnv.funcs:
            thread = Thread(func, (mn, netEnv, logPath,))
            thread.start()
            threads.append(thread)
        # enter command line interface...
        CLI(mn)
    else:
        releaserThread = ReleaserThread(netEnv.releaserFunc, (mn, netEnv, logPath,))
        releaserThread.start()
        # main thread waits releaserThread until it ends
        
        for func in netEnv.funcs:
            thread = Thread(func, (mn, netEnv, logPath,))
            thread.start()
            threads.append(thread)

        releaserThread.waitToStop()
        
        for thread in threads:
            thread.join()

        # terminate
        mn.stop()
        return
    
if __name__=='__main__':
    neSetName = 'mot_bwVar_3'
    #nesetName = '06.22.09'#'6.18.14'
    neSet = NetEnv.getNetEnvSet(neSetName)
    os.chdir(sys.path[0])

    logRootPath = '../logs'
    if not os.path.exists(logRootPath):
        os.makedirs(logRootPath, mode=0o0777)
    logPath = '%s/%s' % (logRootPath, neSetName)
    if not os.path.exists(logPath):
        os.makedirs(logPath, mode=0o0777)

    isManual = getArgsFromCli().m
    if isManual:
        netEnvs = [neSet.netEnvs[0]]
    for i,netEnv in enumerate(neSet.netEnvs):
        print('Start NetEnv(%d/%d) %s' % (i+1,len(neSet.netEnvs),netEnv.name))
        mngo(netEnv, isManual, logPath)
        
    print('all experiments finished.')

    autoAnlz.anlz(neSetName)
    os.system('killall -9 run.py >/dev/null 2>&1')
