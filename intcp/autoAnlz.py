#!/usr/bin/python3

import time
import matplotlib.pyplot as plt
import os
import sys
import functools
import argparse

import NetEnv
from FileUtils import createFolder, fixOwnership, writeText

def timestamp():
    return time.strftime('%m-%d-%H-%M-%S', time.localtime())

def mean(values, method='all'):
    if method=='all':
        return sum(values)/len(values)
    elif method == 'noMaxMin':
        if len(values)<=2:
            raise Exception('ERROR: the amount of data is too small.')
        else:
 
            del values[values.index(max(values))]
            del values[values.index(min(values))]
            return sum(values)/len(values)
    elif method == "median":
        rm = int((len(values)-1)/2)
        for i in range(rm):
            del values[values.index(max(values))]
            del values[values.index(min(values))]
        return sum(values)/len(values)
        
def loadLog(logPath, neSet,isRttTest, isDetail=False):
    result = {}
    for netEnv in neSet.netEnvs:
        print(netEnv.name)
        thrps = []
        try:

            with open('%s/%s.txt'%(logPath,netEnv.name),'r') as f:
                if not isRttTest:
                    lines = f.readlines()
                    for line in lines:
                        if 'receiver' in line:
                            numString = line.split('bits')[0][-7:-2]
                            num = float(numString)/(1 if line.split('bits')[0][-1]=='M' else 1000)
                            thrps.append(num)
                            print(num)
                else:
                    print("load rtt log")
                    rttTotal = netEnv.rttTotal
                    lines = f.readlines()
                    total_packets = 0
                    retran_packets = 0
                    if netEnv.pepCC=="nopep":
                        threhold = 1.5*netEnv.rttTotal
                    else:
                        threhold = netEnv.rttSat+0.5*netEnv.rttTotal
                    for line in lines:
                        total_packets += 1
                        if "owd_c2s" in line:
                            pos1 = line.find("owd_c2s")
                            pos2 = line.find("owd_s2c")
                            num = float(line[pos1+8:pos2])
                            #thrps.append(num)
                            if num>threhold:
                                thrps.append(num)
                                print(num)
                            #pos = line.find("deltaTime")
                            #num = float(line[pos+10:-3])
                            #if(num>rttTotal):
                            #    retran_packets += 1
                            #    thrps.append(num)
                            #    print(num)
                    #thrps.append(retran_packets/total_packets)
            if isDetail:
                result[netEnv] = thrps
            else:
                #TODO observe their variance
                result[netEnv] = mean(thrps,method='all')
                #result[netEnv] = mean(thrps,method='noMaxMin')
        except:
            print('ERROR: log doesn\'t exists.')
        
    return result
    
def plotSeq(resultPath, result, keyX, groups, title, legends=[],isRttTest=False):
    print("entering plotseq")
    plt.figure(figsize=(5,5),dpi=200)
    plt.ylim((0,20))
    if len(groups)==1:
        group = groups[0]
        plt.plot([netEnv.get(keyX) for netEnv in group],
                 [result[netEnv] for netEnv in group])
    else:
        for i,group in enumerate(groups):
            print(len(group))
            for netEnv in group:
                print(netEnv.get(keyX),result[netEnv])
            if group[0].e2eCC == 'hybla':
                color = 'orangered'
            elif group[0].e2eCC == 'cubic':
                color = 'royalblue'
            else:
                color = 'g'
            if group[0].pepCC == 'nopep':
                marker = 'x'
                linestyle = '--'
            else:
                marker = 's'
                linestyle = '-'
            plt.plot([netEnv.get(keyX) for netEnv in group],
                     [result[netEnv] for netEnv in group], label=legends[i],marker=marker,linestyle=linestyle,color=color,markersize=3,linewidth=1)
        plt.legend()
    plt.xlabel(NetEnv.NetEnv.keyToStr(keyX)) #(keyX.title()+'('+xunit+')')
    if isRttTest:
        plt.ylabel('one way delay(ms)')
        #plt.ylabel('error rate')
    else:
        plt.ylabel('Bandwidth(Mbps)')
    plt.title(title)
    plt.savefig('%s/%s.png' % (resultPath, title))
    return
    

def plotByGroup(resultPath, mapNeToResult, keyX, curveDiffSegs=[], plotDiffSegs=[],isRttTest=False):

    # plotDiffSegs is a subset of curveDiffSegs


    pointGroups = []
    for netEnv in mapNeToResult:
        found = False
        for group in pointGroups:

            if netEnv.compareOnly(group[0], curveDiffSegs):

                found = True
                group.append(netEnv)
                break
        if not found:
            pointGroups.append([netEnv])

    curves = []
    for group in pointGroups:
        if len(group)>=2:
            # sort
            group = sorted(group, key=functools.cmp_to_key(lambda a1,a2: a1.get(keyX) - a2.get(keyX)))
            curves.append(group)
    print('curves num:',len(curves))
    for curve in curves:
       print('points in curve:',len(curve))
    # TODO
    # automatically find the difference between these pointGroups

    curveGroups = []
    for curve in curves:
        found = False
        for group in curveGroups:

            if curve[0].compareOnly(group[0][0], plotDiffSegs):#DEBUG

                found = True
                group.append(curve)
                break
        if not found:
            curveGroups.append([curve])
    print('plots num:',len(curveGroups))

    for curveGroup in curveGroups:
        legends = []
        for curve in curveGroup:
            #print("afaag")
            string = ' '.join([curve[0].segToStr(seg) for seg in curveDiffSegs])
            if 'pepCC=nopep' in string and 'e2eCC=hybla' in string:
                string = "hybla end-to-end"
            elif 'pepCC=nopep' in string and 'e2eCC=cubic' in string:
                string = "cubic end-to-end"
            elif 'pepCC=hybla' in string and 'e2eCC=hybla' in string:
                string = "hybla split"
            elif 'pepCC=cubic' in string and 'e2eCC=cubic' in string:
                string = "cubic split"
            #string = string.replace('pepCC=nopep', 'no-pep')
            legends.append(string)
        if isRttTest:
            title = '%s - OneWayDelay' % (keyX)
        else:
            title = '%s - bw' % (keyX)
        if plotDiffSegs != []:
            #print("adfafafa")
            title += '(%s)' % (' '.join([curve[0].segToStr(seg) for seg in plotDiffSegs]))
        plotSeq(resultPath, mapNeToResult, keyX, curveGroup, title=title, legends=legends,isRttTest=isRttTest)
       


def anlz(npsetName,isRttTest=False):
    os.chdir(sys.path[0])
    neSet = NetEnv.getNetEnvSet(npsetName)
    logPath = '%s/%s' % ('../logs', npsetName)
    mapNeToResult = loadLog(logPath, neSet,isRttTest,isDetail=False)

    resultPath = '%s/%s' % ('../result', npsetName)
    createFolder(resultPath)

    #mapNeToResult = loadLog(logPath, neSet, isDetail=False)
    print('-----')
    # make plot
    if neSet.keyX != 'null':
        plotByGroup(resultPath, mapNeToResult, neSet.keyX, curveDiffSegs=neSet.keysCurveDiff,isRttTest=isRttTest)
    print('-----')
    summaryString = '\n'.join(['%s   \t%.3f'%(ne.name,mapNeToResult[ne]) for ne in mapNeToResult])
    print(summaryString)
    print('-----')


    writeText('%s/summary.txt'%(resultPath), summaryString)
    writeText('%s/template.txt'%(resultPath), neSet.neTemplate.serialize())
    fixOwnership(resultPath,'r')

if __name__=='__main__':

    nesetName = 'mot_itm_6'
    #nesetName = 'mot_bwVar_8'
    parser = argparse.ArgumentParser()
    parser.add_argument('--r', action='store_const', const=True, default=False, help='rtt test')
    args = parser.parse_args()
    anlz(nesetName,args.r)

