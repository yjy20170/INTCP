#!/usr/bin/python3

import time
import matplotlib.pyplot as plt
import os
import sys
import functools
import argparse
import seaborn as sns
import NetEnv
import numpy as np
from scipy.stats import scoreatpercentile
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
            if isDetail or isRttTest:
                result[netEnv] = thrps
            else:
                #TODO observe their variance
                result[netEnv] = mean(thrps,method='all')
                #result[netEnv] = mean(thrps,method='noMaxMin')
        except:
            print('ERROR: log doesn\'t exists.')
        
    return result

def getPlotParam(group,isRttTest=False):
    if not isRttTest:
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
    else:
        if group[0].pepCC == 'nopep':
            color = 'purple'
        else:
            color = 'green'
        marker = 's'
        linestyle = '-'
    return color,marker,linestyle
    
def drawCondfidenceCurve(group,result,keyX,label,color,marker,alpha=0.3,mode=2):
    if mode==1:
        x=[]
        y=[]
        for netEnv in group:
            cnt = len(result[netEnv])
            x += cnt*[netEnv.get(keyX)]
            y += result[netEnv]
        #sns.regplot(x=x,y=y,scatter_kws={'s':10},line_kws={'linewidth':1,'label':label},ci=95,x_estimator=np.mean)
        sns.regplot(x=x,y=y,scatter_kws={'s':2,'color':color,},line_kws={'linewidth':1,'label':label,'color':color},ci=95)    
    
    elif mode==2:
        x = []
        y_mean=[]
        y_lower = []
        y_upper = []
        
        for netEnv in group:
            y = result[netEnv]
            if len(y)==0:
                continue
            cur_x = netEnv.get(keyX)
            cur_y_lower = scoreatpercentile(y,5)
            cur_y_upper = scoreatpercentile(y,95)
            x.append(netEnv.get(keyX))
            y_mean.append(mean(y,method='all'))
            y_lower.append(cur_y_lower)
            y_upper.append(cur_y_upper)
            plt.plot([cur_x,cur_x],[cur_y_lower,cur_y_upper],color=color)
            
        plt.plot(x,y_mean,label=label,color=color,marker=marker)
        plt.fill_between(x,y_mean,y_lower,color=color,alpha=alpha)
        plt.fill_between(x,y_mean,y_upper,color=color,alpha=alpha)
        
def plotSeq(resultPath, result, keyX, groups, title, legends=[],isRttTest=False):
    print("entering plotseq")
    #plt.figure(figsize=(5,5),dpi=200)
    plt.figure(figsize=(8,5),dpi = 320)
    #plt.figure(dpi=200)
    plt.ylim((0,20))
    legend_font = {"family" : "Times New Roman"}
    if len(groups)==1:
        group = groups[0]
        plt.plot([netEnv.get(keyX) for netEnv in group],
                 [result[netEnv] for netEnv in group])
    else:
        for i,group in enumerate(groups):
            print(len(group))
            for netEnv in group:
                print(netEnv.get(keyX),result[netEnv])
                
            color,marker,linestyle = getPlotParam(group,isRttTest)
                
            if not isRttTest:
                plt.plot([netEnv.get(keyX) for netEnv in group],
                            [result[netEnv] for netEnv in group], label=legends[i],marker=marker,linestyle=linestyle,color=color,markersize=4,linewidth=1.5)
                #plt.legend()
            else:
                drawCondfidenceCurve(group,result,keyX,legends[i],color,marker,mode=2)
                #plt.legend()
        plt.legend(frameon=True,prop=legend_font)
    plt.xlabel(NetEnv.NetEnv.keyToStr(keyX),family="Times New Roman") #(keyX.title()+'('+xunit+')')
    if isRttTest:
        plt.ylabel('one way delay(ms)'),
        #plt.ylabel('error rate')
    else:
        plt.ylabel('Bandwidth(Mbps)',family="Times New Roman")
    plt.title(title,family="Times New Roman")
    plt.yticks(fontproperties = 'Times New Roman')
    plt.xticks(fontproperties = 'Times New Roman')
    #plt.tight_layout()
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
    if not isRttTest:
        summaryString = '\n'.join(['%s   \t%.3f'%(ne.name,mapNeToResult[ne]) for ne in mapNeToResult])
        print(summaryString)
        print('-----')


        writeText('%s/summary.txt'%(resultPath), summaryString)
        writeText('%s/template.txt'%(resultPath), neSet.neTemplate.serialize())
    fixOwnership(resultPath,'r')

if __name__=='__main__':

    #nesetName = 'mot_rtt_6'
    #nesetName = 'mot_bwVar_8'
    parser = argparse.ArgumentParser()
    parser.add_argument('--r', action='store_const', const=True, default=False, help='rtt test')
    args = parser.parse_args()
    
    nesetNames = ['mot_rtt_6']
    for nesetName in nesetNames:
        anlz(nesetName,args.r)

