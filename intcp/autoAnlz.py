#!/usr/bin/python3

import time
import matplotlib.pyplot as plt
import os
import sys
import functools

import NetEnv
from Utils import createFolder, fixOwnership, writeText

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

def loadLog(logPath, neSet, isDetail=False):
    result = {}
    for netEnv in neSet.netEnvs:
        print(netEnv.name)
        thrps = []
        try:

            with open('%s/%s.txt'%(logPath,netEnv.name),'r') as f:

                lines = f.readlines()
                for line in lines:
                    if 'receiver' in line:
                        numString = line.split('bits')[0][-7:-2]
                        num = float(numString)/(1 if line.split('bits')[0][-1]=='M' else 1000)
                        thrps.append(num)
                        print(num)
            if isDetail:
                result[netEnv] = thrps
            else:
                #TODO observe their variance
                result[netEnv] = mean(thrps,method='all')
        except:
            print('ERROR: log doesn\'t exists.')
        
    return result
    
def plotSeq(resultPath, result, keyX, groups, title, legends=[]):
    print("entering plotseq")
    plt.figure(figsize=(5,5),dpi=200)
    plt.ylim((0,10))
    if len(groups)==1:
        group = groups[0]
        plt.plot([netEnv.get(keyX) for netEnv in group],
                 [result[netEnv] for netEnv in group])
    else:
        for i,group in enumerate(groups):
            print(len(group))
            for netEnv in group:
                print(netEnv.get(keyX),result[netEnv])
            plt.plot([netEnv.get(keyX) for netEnv in group],
                     [result[netEnv] for netEnv in group], label=legends[i])
        plt.legend()
    plt.xlabel(NetEnv.NetEnv.keyToStr(keyX)) #(keyX.title()+'('+xunit+')')
    plt.ylabel('Bandwidth(Mbps)')
    plt.title(title)
    plt.savefig('%s/%s.png' % (resultPath, title))
    return
    

def plotByGroup(resultPath, mapNeToResult, keyX, curveDiffSegs=[], plotDiffSegs=[]):

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
       print(len(curve))
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
            string = string.replace('pepCC=nopep', 'no-pep')
            legends.append(string)

        title = '%s - bw' % (keyX)
        if plotDiffSegs != []:
            #print("adfafafa")
            title += '(%s)' % (' '.join([curve[0].segToStr(seg) for seg in plotDiffSegs]))
        plotSeq(resultPath, mapNeToResult, keyX, curveGroup, title=title, legends=legends)
       


def anlz(npsetName):
    os.chdir(sys.path[0])
    neSet = NetEnv.getNetEnvSet(npsetName)
    logPath = '%s/%s' % ('../logs', npsetName)
    mapNeToResult = loadLog(logPath, neSet, isDetail=False)

    resultPath = '%s/%s' % ('../result', npsetName)
    createFolder(resultPath)

    # make plot



    # plotByGroup(resultPath, neToResultDict,'rttSat',curveDiffSegs=['e2eCC','pepCC'])
    # plotByGroup(resultPath, neToResultDict,'itmDown',curveDiffSegs=['e2eCC','pepCC'])
    # plotByGroup(resultPath, neToResultDict,'varBw',curveDiffSegs=['e2eCC','pepCC'])
    # plotByGroup(resultPath, neToResultDict, 'rttSat', curveDiffSegs=['e2eCC', 'pepCC'])
    #plotByGroup(resultPath, neToResultDict, 'varIntv', curveDiffSegs=['e2eCC', 'pepCC'], ignoreDiffSegs=['varBw'])


    #plotByGroup(resultPath, neToResultDict, neSet.keyX, curveDiffSegs=neSet.keysCurveDiff)


    if neSet.keyX != 'null':
        plotByGroup(resultPath, mapNeToResult, neSet.keyX, curveDiffSegs=neSet.keysCurveDiff)

    print('-----')
    summaryString = '\n'.join(['%s   \t%.3f'%(ne.name,mapNeToResult[ne]) for ne in mapNeToResult])
    print(summaryString)
    print('-----')


    writeText('%s/summary.txt'%(resultPath), summaryString)
    writeText('%s/template.txt'%(resultPath), neSet.neTemplate.serialize())
    fixOwnership(resultPath,'r')

if __name__=='__main__':

    nesetName = 'mot_itm_4'
    #nesetName = 'mot_bwVar_6'
    anlz(nesetName)

