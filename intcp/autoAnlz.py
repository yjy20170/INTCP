#!/usr/bin/python3

import time
import matplotlib.pyplot as plt
import os
import functools

import NetEnv
import sys

def timestamp():
    return time.strftime('%m-%d-%H-%M-%S', time.localtime())

def mean(values, method='all'):
    if method=='all':
        return sum(values)/len(values)
    elif method == 'noMaxMin':
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
                if len(thrps)<=2:
                    print('ERROR: the amount of data is too small.')
                else:
                    result[netEnv] = mean(thrps,method='all')
        except:
            print('ERROR: log doesn\'t exists.')
        
    return result
    
def plotSeq(resultPath, result, keyX, groups, title, legends=[]):
    plt.figure(figsize=(10,10),dpi=100)
    plt.ylim((0,12))
    if len(groups)==1:
        group = groups[0]
        plt.plot([netEnv.get(keyX) for netEnv in group],
                 [result[netEnv] for netEnv in group])
    else:
        for i,group in enumerate(groups):
            plt.plot([netEnv.get(keyX) for netEnv in group],
                     [result[netEnv] for netEnv in group], label=legends[i])
        plt.legend()
    plt.xlabel('%s(%s)' % (keyX, NetEnv.NetEnv.SegUnit[keyX])) #(keyX.title()+'('+xunit+')')
    plt.ylabel('Bandwidth(Mbps)')
    plt.title(title)
    plt.savefig('%s/%s.png' % (resultPath, title))
    return
    
def plotByGroup(resultPath, npToResultDict,segX,curveDiffSegs=[],ignoreDiffSegs=[]):
    pointGroups = []
    for netEnv in npToResultDict:
        found = False
        for group in pointGroups:
            if netEnv.compare(group[0],mask=[segX]+ignoreDiffSegs):
                found = True
                group.append(netEnv)
                break
        if not found:
            pointGroups.append([netEnv])

    curves = []
    for group in pointGroups:
        if len(group)>=2:
            # sort
            group = sorted(group,key=functools.cmp_to_key(lambda a1,a2: a1.__dict__[segX]-a2.__dict__[segX]))
            curves.append(group)
    print('curves',len(curves))

    # TODO
    # automatically find the difference between these pointGroups

    curveGroups = []

    for curve in curves:
        found = False
        for group in curveGroups:
            if curve[0].compare(group[0][0],mask=curveDiffSegs+[segX]+ignoreDiffSegs):#DEBUG
                found = True
                group.append(curve)
                break
        if not found:
            curveGroups.append([curve])
    print('curveGroups',len(curveGroups))

    for curveGroup in curveGroups:
        # draw each curveGroup in one plot
        diffSegs = []
        # for seg in NetEnv.NetEnv.Keys:
        #     if seg == segX:
        #         continue
        #     segval = curveGroup[0][0].__dict__[seg]
        #     for curve in curveGroup[1:]:
        #         if curve[0].__dict__[seg] != segval:
        #             diffSegs.append(seg)
        #             break

        # TODO
        # content and impaction of diffSegs should be re-designed
        diffSegs = curveDiffSegs

        legends = []
        for curve in curveGroup:
            string = ' '.join([curve[0].segToStr(seg) for seg in diffSegs])
            string = string.replace(' pepCC=nopep', '')
            legends.append(string)
        # title = '%s-bw under different %s' % (keyX, ','.join(diffSegs))
        title = curve[0].groupTitle(segX, diffSegs)
        plotSeq(resultPath, npToResultDict, segX, curveGroup, title=title, legends=legends)

def anlz(npsetName):
    # print(sys.path[0])
    os.chdir(sys.path[0])

    neSet = NetEnv.getNetEnvSet(npsetName)
    logPath = '%s/%s' % ('../logs', npsetName)
    neToResultDict = loadLog(logPath, neSet, isDetail=False)

    resultRootPath = '../result'
    if not os.path.exists(resultRootPath):
        os.makedirs(resultRootPath, mode=0o0777)
    resultPath = '%s/%s' % (resultRootPath,npsetName)
    if not os.path.exists(resultPath):
        os.makedirs(resultPath, mode=0o0777)

    # make plot
    # plotByGroup(resultPath, neToResultDict,'rttSat',curveDiffSegs=['e2eCC','pepCC'])
    # plotByGroup(resultPath, neToResultDict,'itmDown',curveDiffSegs=['e2eCC','pepCC'])
    # plotByGroup(resultPath, neToResultDict,'varBw',curveDiffSegs=['e2eCC','pepCC'])
    # plotByGroup(resultPath, neToResultDict, 'rttSat', curveDiffSegs=['e2eCC', 'pepCC'])
    plotByGroup(resultPath, neToResultDict, 'bw', curveDiffSegs=['e2eCC', 'pepCC'], ignoreDiffSegs=['varBw'])

    print('-----')
    summaryString = '\n'.join(['%s   \t%.3f'%(ne.name,neToResultDict[ne]) for ne in neToResultDict])
    print(summaryString)
    print('-----')
    with open('%s/summary.txt'%(resultPath),'w') as f:
        f.write(summaryString)

if __name__=='__main__':
    nesetName = 'mot_bwVar_3'
    anlz(nesetName)
