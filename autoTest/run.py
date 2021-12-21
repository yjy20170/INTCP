#!/usr/bin/python3

import sys
import os
import argparse
import time

sys.path.append(os.path.dirname(os.sys.path[0]))
from testbed import Instance

import MyParam
import FileUtils
import autoAnlz

def getArgsFromCli():
    parser = argparse.ArgumentParser()

    parser.add_argument('--m', action='store_const', const=True, default=False, help='enter command line interface(run auto experiment by default)')
    parser.add_argument('--r', action='store_const', const=True, default=False, help='enter rtt test')
    parser.add_argument('--a', action='store_const', const=True, default=False, help='only run analyzing program')
    args = parser.parse_args()
    return args


if __name__=='__main__':
    os.chdir(sys.path[0]) 
    # import inspect

    # for name, obj in inspect.getmembers(userThreads):
    #     if inspect.isclass(Thread):
    #         print(Thread)


    tpSetNames = ["cc_itm_test_1"]#"mot_itm_test"


    isAnlz = getArgsFromCli().a
    isManual = getArgsFromCli().m
    isRttTest = getArgsFromCli().r

    for sno,tpSetName in enumerate(tpSetNames):
        print('\nStart NetEnvSet (%d/%d)' % (sno+1,len(tpSetNames)))
        tpSet = MyParam.getTestParamSet(tpSetName)
        # netTopo = NetTopo.netTopos[neSet.neTemplate.netName]

        logPath = '%s/%s' % ('./logs', tpSetName)

        if not isAnlz:
            FileUtils.createFolder(logPath)
            FileUtils.writeText('%s/template.txt'%(logPath), tpSet.tpTemplate.serialize())
        
            for i,tp in enumerate(tpSet.testParams):
                print('\nStart NetEnv(%d/%d) in NetEnvSet \'%s\'' % (i+1,len(tpSet.testParams),tpSetName))
                
                tp.appParam.update('isManual', 1 if isManual else 0)

                Instance.run(tp, logPath)

            FileUtils.fixOwnership(logPath, 'r')

        resultPath = '%s/%s' % ('./result', tpSetName)
        autoAnlz.anlz(tpSet, logPath, resultPath)

    if not isAnlz:
        Instance.clear()
    print('all experiments finished.')
