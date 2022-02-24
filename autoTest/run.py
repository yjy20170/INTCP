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
import userThreads # for threadFunc execution
import get_trace

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    # enter command line interface (run auto experiment by default)
    parser.add_argument('--m', action='store_const', const=True, default=False)
    # only run analyzing program
    parser.add_argument('--a', action='store_const', const=True, default=False)
    args = parser.parse_args()
    isManual = args.m
    isAnlz = args.a

    os.chdir(sys.path[0])

    if not isAnlz:
        a = 1
        #os.system("../appLayer/intcpApp/makes.sh")
        #os.system("../pepsal_min/bash/makepep")


    tpSetNames = ["dynamic_exp_3"]#["expr"]#
    try:
        for sno,tpSetName in enumerate(tpSetNames):
            if len(tpSetNames)!=1:
                print('\nStart TestParamSet \'%s\' (%d/%d)' % (tpSetName,sno+1,len(tpSetNames)))
            tpSet = MyParam.getTestParamSet(tpSetName)

            logPath = '%s/%s' % ('./logs', tpSetName)
            resultPath = '%s/%s' % ('./result', tpSetName)

            if not isAnlz:
                FileUtils.createFolder(logPath)
                FileUtils.writeText('%s/template.txt'%(logPath), tpSet.tpTemplate.serialize())
            
                for i,tp in enumerate(tpSet.testParams):
                    if len(tpSet.testParams)!=1:
                        print('\nStart TestParam(%d/%d) in \'%s\'' % (i+1,len(tpSet.testParams),tpSetName))
                    if not tp.appParam.dynamic:
                        print(tp.serialize())
                    Instance.run(tp, logPath, isManual)

                FileUtils.fixOwnership(logPath, 'r')

            if not isManual:
                time.sleep(1)
                autoAnlz.anlz(tpSet, logPath, resultPath)
    except KeyboardInterrupt:
        print('\nStopped')

    print('all experiments finished.')
    os.system('sudo killall -9 xterm >/dev/null 2>&1')
