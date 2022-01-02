#!/usr/bin/python3

import time
import matplotlib.pyplot as plt
import os
import sys
import functools
import argparse
import seaborn as sns
import numpy as np 
from scipy.stats import scoreatpercentile
import statsmodels.api as sm

sys.path.append(os.path.dirname(os.sys.path[0]))
from FileUtils import createFolder, fixOwnership, writeText
import MyParam


plt.rc('font',family='Times New Roman')
# plt.rcParams['font.sans-serif'] = 'Times New Roman'


def timestamp():
    return time.strftime('%m-%d-%H-%M-%S', time.localtime())

def mean(values, method='all'):
    if method=='all':
        return sum(values)/len(values)
    elif method == 'noMaxMin':
        if len(values)<=2:
            raise Exception('the amount of data is too small.')
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

def getOwdTotal(tp):
    rttTotal = 0
    rttMin = 999999
    for ln in tp.topoParam.linkNames():
        lp = tp.linksParam.getLP(ln)
        rttTotal += lp.rtt
        rttMin = min(rttMin,lp.rtt)
    owdTotal = rttTotal*0.5
    if tp.appParam.protocol=="INTCP" and not tp.appParam.midCC=="nopep":
        retranThreshold = rttTotal*0.5 + rttMin
    else:
        retranThreshold = rttTotal*1.5
    return owdTotal,retranThreshold
    
def getTCDelay(tp):
    sender = "h1" if tp.appParam.protocol=="TCP" else "h2"
    for linkName in tp.topoParam.linkNames():
        if sender in linkName:
            return tp.linksParam.getLP(linkName).rtt/4
    raise Exception("sender link not found")
            
def parseLine(line,protocol):
    if protocol=="TCP":
        p1 = line.find("length")
        p2 = line.find("time")
        seq = int(line[4:p1-1])
        time = float(line[p2+5:])
        return seq,time
    elif protocol=="INTCP":
        p1 = line.find("rangeStart")
        p2 = line.find("rangeEnd")
        p3 = line.find("time")
        rs = int(line[p1+11:p2-1])
        time = float(line[p3+5:])
        return rs,time
        
def generateLog(logPath,tpSet):
    for tp in tpSet.testParams:
        senderLogFilePath = '%s/%s_%s.txt'%(logPath,tp.name,"send")
        receiverLogFilePath = '%s/%s_%s.txt'%(logPath,tp.name,"recv")
        logFilePath = '%s/%s.txt'%(logPath,tp.name)
        sendTimeDict = {}
        recvTimeDict = {}
        owdDict = {}
        tcDelay = getTCDelay(tp)
        #load sender
        with open(senderLogFilePath,"r") as f:
            lines = f.readlines()
            for line in lines:
                try:
                    seq,time = parseLine(line,tp.appParam.protocol)
                    if not seq in sendTimeDict.keys():
                        sendTimeDict[seq] = time
                except:
                    continue
                    
        #load receiver            
        with open(receiverLogFilePath,"r") as f:
            lines = f.readlines()
            for line in lines:
                try:
                    seq,time = parseLine(line,tp.appParam.protocol)
                    if not seq in recvTimeDict.keys():
                        recvTimeDict[seq] = time
                except:
                    continue
                    
        for seq in sendTimeDict.keys():
            if seq in recvTimeDict.keys():
                owdDict[seq] = 1000*(recvTimeDict[seq]-sendTimeDict[seq])+tcDelay
            else:
                print(seq,end=',')  
        print("\n----%s------"%(tp.name))         
        with open(logFilePath,"w") as f:
            for seq,owd in owdDict.items():
                f.write("seq %d owd_obs %f\n"%(seq,owd)) 
        #print(sendTimeDict.keys())
        #print(recvTimeDict.keys())    
              
def loadLog(logPath, tpSet, isDetail=False, intcpRtt=False, retranPacketOnly=False):
    result = {}
    for tp in tpSet.testParams:
        logFilePath = '%s/%s.txt'%(logPath,tp.name)
        #print(tp.name)
        thrps = []
        result[tp] = thrps
        with open(logFilePath,'r') as f:
            lines = f.readlines()
            if not tpSet.tpTemplate.appParam.isRttTest:
                for line in lines:
                    if 'receiver' in line:
                        numString = line.split('bits')[0][-7:-2]
                        num = float(numString)/(1 if line.split('bits')[0][-1]=='M' else 1000)
                        thrps.append(num)
                        print(num)
            else:
                #print("load rtt log")
                if intcpRtt:    #false
                    if not tp.appParam.protocol=="INTCP":
                        continue
                    for line in lines:
                        if "intcpRtt" in line:
                            p1 = line.find("intcpRtt")
                            try:
                                p2 = line.find("owd_noOrder")
                                num = float(line[p1+9:p2-1])
                                thrps.append(num)
                            except:
                                continue
                else:
                    #prev_owd = 0
                    owd_total,retran_threshold = getOwdTotal(tp)
                    #limit = min(owd_total+50,retran_threshold) if retranPacketOnly else owd_total
                    limit = retran_threshold if retranPacketOnly else owd_total
                    if tp.appParam.protocol=="TCP" or tp.appParam.protocol=="INTCP":
                        for line in lines:
                            if "owd_obs" in line:
                                pos_obs = line.find("owd_obs")
                                try:
                                    owd = float(line[pos_obs+8:])
                                    if owd>limit:
                                        thrps.append(owd)
                                except:
                                    continue

        if isDetail or tpSet.tpTemplate.appParam.isRttTest:    
            result[tp] = thrps
        else:
            result[tp] = mean(thrps,method='all')
    for k in result:
       #print(k.name)
        if isDetail:     
            print(k.name,result[k][:5])
        else:
            print(k.name,result[k])
    print("---end loading---")    
    return result

def getPlotParam(group, isRttTest=False):
    if not isRttTest:
        #for motivation exprs
        '''
        if group[0].appParam.e2eCC == 'hybla':
            color = 'orangered'
        elif group[0].appParam.e2eCC == 'cubic':
            color = 'royalblue'
        else:
            color = 'g'

        if group[0].appParam.midCC == 'nopep':
            marker = 'x'
            linestyle = '--'
        else:
            marker = 's'
            linestyle = '-'
        '''
        if group[0].appParam.protocol == 'INTCP':
            marker = 'x'
            linestyle = '--'
            color = 'red'
        else:
            marker = 's'
            linestyle = '-'
            if group[0].appParam.e2eCC == 'hybla':
                color = 'orangered'
            elif group[0].appParam.e2eCC == 'cubic':
                color = 'royalblue'
            else:
                color = 'g'
    else:
        if group[0].appParam.midCC == 'nopep':
            color = 'purple'
        else:
            color = 'green'
        marker = 's'
        linestyle = '-'
    return color,marker,linestyle

#TODO rename: NetEnv -> TestParam
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

def plotOneFig(resultPath, result, keyX, groups, title, legends=[],isRttTest=False):
    plt.figure(figsize=(8,5),dpi = 320)
    if not isRttTest:
        plt.ylim((0,20))
    else:
        plt.ylim((0,1000))
    legend_font = {'size':12}#"family" : "Times New Roman",
    if len(groups)==1:
        group = groups[0]
        plt.plot([netEnv.get(keyX) for netEnv in group],
                 [result[netEnv] for netEnv in group])
    else:
        for i,group in enumerate(groups):

            color,marker,linestyle = getPlotParam(group,isRttTest)

            if not isRttTest:
                plt.plot([netEnv.get(keyX) for netEnv in group],
                            [result[netEnv] for netEnv in group], label=legends[i],marker=marker,linestyle=linestyle,color=color,markersize=4,linewidth=1.5)
                #plt.legend()
            else:
                drawCondfidenceCurve(group,result,keyX,legends[i],color,marker,mode=2)
                #plt.legend()
        plt.legend(frameon=True,prop=legend_font)
    plt.xlabel(groups[0][0].keyToStr(keyX),size=12) #family="Times New Roman",
    if isRttTest:
        plt.ylabel('one way delay(ms)',size=12)#family="Times New Roman",
        #plt.ylabel('error rate')
    else:
        plt.ylabel('throughput(Mbps)',size=12)#family="Times New Roman",
    plt.title(title,size=15)#family="Times New Roman",
    plt.yticks(size=12)#fontproperties = 'Times New Roman',
    plt.xticks(size=12)#fontproperties = 'Times New Roman',
    #plt.tight_layout()
    plt.savefig('%s/%s.png' % (resultPath, title))
    return
    

def plotByGroup(tpSet, mapNeToResult, resultPath):
    pointGroups = []
    for tp in tpSet.testParams:
        found = False
        for group in pointGroups:

            if tp.compareKeys(group[0], tpSet.keysCurveDiff+tpSet.keysPlotDiff):

                found = True
                group.append(tp)
                break
        if not found:
            pointGroups.append([tp])

    curves = []
    for group in pointGroups:
        if len(group)>=2:
            # sort
            group = sorted(group, key=functools.cmp_to_key(lambda a1,a2: a1.get(tpSet.keyX) - a2.get(tpSet.keyX)))
            curves.append(group)
    print('curves num:',len(curves))

    curveGroups = []
    for curve in curves:
        found = False
        for group in curveGroups:
            if curve[0].compareKeys(group[0][0], tpSet.keysPlotDiff):
                found = True
                group.append(curve)
                break
        if not found:
            curveGroups.append([curve])
    print('plots num:',len(curveGroups))

    for curveGroup in curveGroups:
        legends = []
        for curve in curveGroup:
            keys = tpSet.keysCurveDiff
            keyMidCC = 'appParam.midCC'
            keyE2eCC = 'appParam.e2eCC'
            if keyMidCC in keys and keyE2eCC in keys:
                keys.remove(keyMidCC)
                keys.remove(keyE2eCC)
                midCC = curve[0].get(keyMidCC)
                stringCC = e2eCC = curve[0].get(keyE2eCC)
                if midCC == 'nopep':
                    stringCC += ' e2e'
                elif midCC == e2eCC:
                    stringCC += 'split'
                else:
                    stringCC += ' + '+midCC
            else:
                stringCC = ''
            string = stringCC + ' ' + ' '.join([curve[0].segToStr(key) for key in keys])
            
            legends.append(string)
        keyX = tpSet.keyX
        isRttTest = tpSet.tpTemplate.appParam.isRttTest
        if isRttTest:
            title = '%s - OneWayDelay' % (keyX)
        else:
            title = '%s - throughput' % (keyX)
        if tpSet.keysPlotDiff != []:
            title += '(%s)' % (' '.join([curve[0].segToStr(seg) for seg in tpSet.keysPlotDiff]))
        plotOneFig(resultPath, mapNeToResult, keyX, curveGroup, title=title, legends=legends,isRttTest=isRttTest)

#TODO appParam.total_loss is removed now
def getCdfParam(tp):
    if tp.appParam.protocol=="INTCP":
        linestyle = '--'
    else:
        linestyle = '-'
    
    loss_dict = {0.5:"blue",5:"green",2:"orangered"}
    nodes_dict = {1:"blue",2:"orangered",3:"green"}
    midcc_dict = {'pep':"green",'nopep':'orangered'}
    
    color = loss_dict[tp.appParam.total_loss]
    #color = nodes_dict[tp.topoParam.numMidNode]
    #color = midcc_dict[tp.appParam.midCC]
    return color,linestyle 
    
def drawCDF(tpSet, mapNeToResult, resultPath,intcpRtt=False,retranPacketOnly=False):
    plt.figure(figsize=(8,5),dpi = 320)
    x_min = -1
    x_max = -1
    for tp in tpSet.testParams:
        if len(mapNeToResult[tp])>0:
            cur_min = min(mapNeToResult[tp])
            cur_max = max(mapNeToResult[tp])
            #print("min",cur_min,"max",cur_max)
            if x_min == -1:
                x_min = cur_min
            else:
                x_min = min(cur_min,x_min)
            if x_max == -1:
                x_max = cur_max
            else:
                x_max = max(cur_max,x_max)
    x_min  = 0
    #DEBUG
    #x_max = min(x_max,2000)
    x_max = 1000
    x = np.linspace(x_min,x_max,num=500)
    
    plt.xlim((0,1000))
    if not retranPacketOnly:
        plt.ylim((0.8,1.01)) 
    #plt.xlim((x_min,x_max))
    keys = tpSet.keysCurveDiff
    legends = []
    for tp in tpSet.testParams:
        print(tp.name,min(mapNeToResult[tp]))
        if len(mapNeToResult[tp]) >0:
            color,linestyle = getCdfParam(tp)
            ecdf = sm.distributions.ECDF(mapNeToResult[tp])
            y = ecdf(x)
            #plt.step(x,y)
            plt.step(x,y,linestyle=linestyle,color=color)
            #plt.legend(' '.join([tp.segToStr(key) for key in keys]))
            legends.append(' '.join([tp.segToStr(key) for key in keys]))
    title = 'cdf'
    if intcpRtt:
        title += "_intcpRtt"
    elif retranPacketOnly:
        title += "_retran"
    else:
        title += "_all"
    plt.legend(legends)
    plt.title(title)
    plt.xlabel('one way delay(ms)',size=12)
    plt.savefig('%s/%s.png' % (resultPath, title))
    #plt.show()

def drawSeqGraph(tpSet, mapNeToResult, resultPath,snStart=1000,snEnd=3000):
    plt.figure(figsize=(8,5),dpi = 320)
    #plt.ylim((0,2000))
    keys = tpSet.keysCurveDiff
    legends = []
    for tp in tpSet.testParams:
        if len(mapNeToResult[tp]) >0:
            color,linestyle = getCdfParam(tp)
            plt.plot([i for i in range(len(mapNeToResult[tp]))],mapNeToResult[tp])
            #plt.plot([i for i in range(2000)],mapNeToResult[tp][:2000],color=color,linestyle=linestyle)
            #plt.plot([i for i in range(snStart,snEnd)],mapNeToResult[tp][snStart:snEnd])
            legends.append(' '.join([tp.segToStr(key) for key in keys]))
            
    title = 'Seq Diagram'
    plt.title(title)
    plt.legend(legends)
    plt.xlabel('packet sn',size=12)      
    plt.ylabel('one way delay(ms)',size=12)
    plt.savefig('%s/%s.png' % (resultPath, title))
     
def anlz(tpSet, logPath, resultPath):
    os.chdir(sys.path[0])
    
    createFolder(resultPath)

    #mapNeToResult = loadLog(logPath, neSet, isDetail=False)
    #print('-----')
    #plotByGroup(tpSet, mapTpToResult, resultPath)
    if not tpSet.tpTemplate.appParam.isRttTest:
        print('-----')
        mapTpToResult = loadLog(logPath, tpSet, isDetail=False)
        plotByGroup(tpSet, mapTpToResult, resultPath)
        summaryString = '\n'.join(['%s   \t%.3f'%(tp.name,mapTpToResult[tp]) for tp in mapTpToResult])
        print(summaryString)
        writeText('%s/summary.txt'%(resultPath), summaryString)
        writeText('%s/template.txt'%(resultPath), tpSet.tpTemplate.serialize())
    else:
        #print('entering rtt analyse')
        
        generateLog(logPath,tpSet)
        
        mapTpToResult = loadLog(logPath, tpSet,isDetail=False)
        
        drawCDF(tpSet,mapTpToResult,resultPath)
        
        #drawSeqGraph(tpSet,mapTpToResult, resultPath)
        
        #retranPacketOnly
        mapTpToResult = loadLog(logPath, tpSet,isDetail=False,intcpRtt=False,retranPacketOnly=True)
        drawCDF(tpSet,mapTpToResult,resultPath,retranPacketOnly = True)
        
        #intcpRtt
        #mapTpToResult = loadLog(logPath, tpSet,isDetail=False,intcpRtt=True)
        #drawCDF(tpSet,mapTpToResult,resultPath,intcpRtt = True)
    fixOwnership(resultPath,'r')

"""
if __name__=='__main__':
    tpSetNames = ['expr']
    for sno,tpSetName in enumerate(tpSetNames):
        print('Analyzing NetEnvSet (%d/%d)\n' % (sno+1,len(tpSetNames)))
        tpSet = MyParam.getTestParamSet(tpSetName)
        # netTopo = NetTopo.netTopos[neSet.neTemplate.netName]

        logPath = '%s/%s' % ('./logs', tpSetName)
        resultPath = '%s/%s' % ('./result', tpSetName)
        anlz(tpSet, logPath, resultPath)
"""
