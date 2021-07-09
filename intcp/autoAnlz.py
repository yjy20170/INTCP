#!/usr/bin/python

import time
import matplotlib.pyplot as plt
import os
import functools

import NetParam
import sys

def timestamp():
    return time.strftime('%m-%d-%H-%M-%S', time.localtime())
    
def loadLog(logPath, netParams,isDetail=False):
    result = {}
    for netParam in netParams:
        print(netParam.str())
        thrps = []
        try:
            with open('%s/%s.txt'%(logPath,netParam.str(ver="varIntv")),'r') as f:
            # with open('%s/log_%s.txt'%(logPath,netParam.str('old')),'r') as f:
                lines = f.readlines()
                for line in lines:
                    if 'receiver' in line:
                        #print(line[:-27].split(' '))
                        #print(line.split(' '))
                        numString = line.split('bits')[0][-7:-2]
                        num = float(numString)/(1 if line.split('bits')[0][-1]=='M' else 1000)
                        thrps.append(num)
                        print(num)
            if isDetail:
                result[netParam] = thrps
            else:
                #TODO observe their variance
                if len(thrps)<=2:
                    print('ERROR: the amount of data is too small.')
                else:
                    del thrps[thrps.index(max(thrps))]
                    del thrps[thrps.index(min(thrps))]
                    mid = sum(thrps)/len(thrps)
                    print('Average after removing max and min: %.3f'%mid)
                    result[netParam] = mid
        except:
            print('ERROR: log doesn\'t exists.')
        
    return result
    
def plotSeq(resultPath, result, segX, groups, title, legends=[]):
    plt.figure(figsize=(10,10),dpi=100)
    plt.ylim((0,12))
    if len(groups)==1:
        group = groups[0]
        plt.plot([netParam.__dict__[segX] for netParam in group],
            [result[netParam] for netParam in group])
    else:
        for i,group in enumerate(groups):
            plt.plot([netParam.__dict__[segX] for netParam in group],
                [result[netParam] for netParam in group],label=legends[i])
        plt.legend()
    plt.xlabel('%s(%s)' % (segX, NetParam.NetParam.Unit[segX])) #(segX.title()+'('+xunit+')')
    plt.ylabel('Bandwidth(Mbps)')
    plt.title(title)
    plt.savefig('%s/%s.png' % (resultPath, title))
    return
    
def plotByGroup(resultPath, npToResultDict,segX,curveDiffSegs=[],ignoreDiffSegs=[]):
    print("a")
    pointGroups = []
    for netParam in npToResultDict:
        found = False
        for group in pointGroups:
            if netParam.compare(group[0],mask=[segX]+ignoreDiffSegs):
                found = True
                group.append(netParam)
                break
        if not found:
            pointGroups.append([netParam])
    curves = []
    for group in pointGroups:
        if len(group)>=2:
            # sort
            group = sorted(group,key=functools.cmp_to_key(lambda a1,a2: a1.__dict__[segX]-a2.__dict__[segX]))
            curves.append(group)

    #TODO automatically
    '''    
    # find the difference between these pointGroups
    if len(curves)>1:
        diffSegs = []
        for seg in NetParam.NetParam.Keys:
            if seg==segX:
                continue
            segval = curves[0][0].__dict__[seg]
            for group in curves[1:]:
                if group[0].__dict__[seg] != segval:
                    diffSegs.append(seg)
                    break
        legends = []
        for group in curves:
            legends.append(' '.join([group[0].segStr(seg) for seg in diffSegs]))
        title = '%s-bw under different %s'%(segX,','.join(diffSegs))
        plotSeq(npToResultDict,segX,curves,title=title,legends=legends)
    else:
        title = '%s-bw'%segX
        plotSeq(npToResultDict,segX,curves,title=title)
    '''
    curveGroups = []

    for curve in curves:
        found = False
        for group in curveGroups:
            if curve[0].compare(group[0][0],mask=curveDiffSegs+[segX]+ignoreDiffSegs):
                found = True
                group.append(curve)
                break
        if not found:
            curveGroups.append([curve])

    for curveGroup in curveGroups:
        # draw each curveGroup in one plot
        diffSegs = []
        for seg in NetParam.NetParam.Keys:
            if seg == segX:
                continue
            segval = curveGroup[0][0].__dict__[seg]
            for curve in curveGroup[1:]:
                if curve[0].__dict__[seg] != segval:
                    diffSegs.append(seg)
                    break

        legends = []
        for curve in curveGroup:
            string = ' '.join([curve[0].segStr(seg) for seg in diffSegs])
            string = string.replace(' pepCC=nopep', '')
            legends.append(string)
        # title = '%s-bw under different %s' % (segX, ','.join(diffSegs))
        title = curve[0].groupTitle(segX, diffSegs)
        print("a")
        plotSeq(resultPath, npToResultDict, segX, curveGroup, title=title, legends=legends)

def anlz(npsetName):
    netParams = NetParam.getNetParams(npsetName)
    logPath = '%s/%s' % ('../logs', npsetName)
    npToResultDict = loadLog(logPath, netParams)

    print(sys.path[0])
    os.chdir(sys.path[0])
    resultRootPath = '../result'
    if not os.path.exists(resultRootPath):
        os.makedirs(resultRootPath, mode=0o0777)
    resultPath = '%s/%s' % (resultRootPath,npsetName)
    if not os.path.exists(resultPath):
        os.makedirs(resultPath, mode=0o0777)
    # make plot
    # plotByGroup(resultPath, npToResultDict,'rttSat',curveDiffSegs=['e2eCC','pepCC'])
    # plotByGroup(resultPath, npToResultDict,'itmDown',curveDiffSegs=['e2eCC','pepCC'])
    # plotByGroup(resultPath, npToResultDict,'varBw',curveDiffSegs=['e2eCC','pepCC'])
    #plotByGroup(resultPath, npToResultDict, 'rttSat', curveDiffSegs=['e2eCC', 'pepCC'])
    
    #plotByGroup(resultPath, npToResultDict, 'bw', curveDiffSegs=['e2eCC', 'pepCC'],ignoreDiffSegs=['varBw'])
    plotByGroup(resultPath, npToResultDict, 'varIntv', curveDiffSegs=['e2eCC', 'pepCC'],ignoreDiffSegs=['varBw'])
    with open('%s/summary.txt'%(resultPath),'w') as f:
        f.write('\n'.join(['%s   \t%.3f'%(key.str(),npToResultDict[key]) for key in npToResultDict]))

if __name__=='__main__':
    npsetName = 'mot_bwVar_2'
    anlz(npsetName)
