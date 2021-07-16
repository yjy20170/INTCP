#!/usr/bin/python3

import sys
import importlib
import os
import argparse

from mininet.cli import CLI

import NetEnv
from MultiThread import Thread, LatchThread
from Utils import createFolder, fixOwnership, writeText
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
    print(netEnv.serialize())
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
        LatchThread.pretendRunning()
    else:
        latchThread = LatchThread(NetEnv.LatchFunc, (mn, netEnv, logPath,))
        latchThread.start()
        # normal threads keep running until latchThread ends
    for func in NetEnv.NormalFuncs:
        thread = Thread(func, (mn, netEnv, logPath,))
        thread.start()
        threads.append(thread)
    if isManual:
        # enter command line interface...
        CLI(mn)
    else:
        latchThread.wait()
        for thread in threads:
            # LatchThread.Running = False
            # so the threads will end soon
            thread.join()
        # terminate
        mn.stop()
    return
    
if __name__=='__main__':

    neSetName = 'expr'#"mot_itm_test"
    neSet = NetEnv.getNetEnvSet(neSetName)

    os.chdir(sys.path[0])
    logPath = '%s/%s' % ('../logs', neSetName)
    createFolder(logPath)
    writeText('%s/template.txt'%(logPath), neSet.neTemplate.serialize())

    isManual = getArgsFromCli().m
    if isManual:
        netEnvs = [neSet.netEnvs[0]]
    for i,netEnv in enumerate(neSet.netEnvs):
        print('\nStart NetEnv(%d/%d)' % (i+1,len(neSet.netEnvs)))
        mngo(netEnv, isManual, logPath)
    fixOwnership(logPath, 'r')
    print('all experiments finished.')

    autoAnlz.anlz(neSetName)

    os.system('killall -9 run.py >/dev/null 2>&1')
