#!/usr/bin/python3

#BUG
# import matplotlib.font_manager as mfont
# mfont.findfont('Times New Roman')

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
    first_hop_rtt = tp.linksParam.getLP(tp.topoParam.linkNames()[0]).rtt
    last_hop_rtt = tp.linksParam.getLP(tp.topoParam.linkNames()[-1]).rtt
    if tp.appParam.protocol=="INTCP" and not tp.appParam.midCC=="nopep":    # hop INTCP 
        retranThreshold = rttTotal*0.5 + rttMin
    elif tp.appParam.protocol=="TCP" and not tp.appParam.midCC=="nopep":    # split tcp
        #retranThreshold = rttTotal*0.5 + min(first_hop_rtt,last_hop_rtt,rttTotal-first_hop_rtt-last_hop_rtt)
        retranThreshold = rttTotal*0.5 +(rttTotal-first_hop_rtt-last_hop_rtt)
    else:
        retranThreshold = rttTotal*1.5
    return owdTotal,retranThreshold
    
def getTCDelay(tp):
    #sender = "h1" if tp.appParam.protocol=="TCP" else "h2"
    if not tp.appParam.dynamic:
        sender = "h2"
        for linkName in tp.topoParam.linkNames():
            if sender in linkName:
                return tp.linksParam.getLP(linkName).rtt/4
        raise Exception("sender link not found")
    else:
        return tp.appParam.dynamic_ground_link_rtt/4

def parseLine(line,protocol):
    if protocol=="TCP":
        p1 = line.find("length")
        p2 = line.find("time")
        seq = int(line[4:p1-1])
        time = float(line[p2+5:])
        return seq,time
    elif protocol=="INTCP":
        p1 = line.find("rangeStart")
        p3 = line.find("time")
        if "rangeEnd" in line:
            p2 = line.find("rangeEnd")
        else:
            p2 = p3
        rs = int(line[p1+11:p2-1])
        time = float(line[p3+5:])
        return rs,time
        
def generateLog(logPath,tpSet):
    for tp in tpSet.testParams:
        if tp.appParam.protocol == "TCP" and tp.appParam.test_type == "owdTest":   # record app layer owd for tcp
            continue
        if tp.appParam.protocol == "TCP" and tp.appParam.test_type == "owdThroughputBalance" and tp.appParam.sendq_length!=0:
            continue
        if tp.appParam.protocol == "INTCP" and tp.appParam.test_type == "owdThroughputBalance" and tp.appParam.sendq_length==0:
            continue
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
            for idx,line in enumerate(lines):
                #if tp.appParam.dynamic and idx<1000:    #no order
                #    continue
                try:
                    if "time" in line:
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
                    if "time" in line:
                        seq,time = parseLine(line,tp.appParam.protocol)
                        if not seq in recvTimeDict.keys():
                            recvTimeDict[seq] = time
                except:
                    continue
                    
        for seq in sendTimeDict.keys():
            if seq in recvTimeDict.keys():
                owd_s = recvTimeDict[seq]-sendTimeDict[seq]
                if owd_s > -10 and owd_s <0:    # abnormal owd
                    continue
                if owd_s < 0: # only occur when recvtime exceed 1000
                    owd_s = owd_s + 1000
                owdDict[seq] = 1000*owd_s + tcDelay
            else:
                a = 1
                #print(seq,end=',')  
        print("\n----%s------"%(tp.name))
        with open(logFilePath,"w") as f:
            for seq,owd in owdDict.items():
                f.write("seq %d owd_obs %f\n"%(seq,owd)) 
        #print(sendTimeDict.keys())
        #print(recvTimeDict.keys())

def screen_owd(thrps,retranPacketOnly,owd_total,retran_threshold):
    res = []
    if not retranPacketOnly:
        for owd in thrps:
            if owd > owd_total-2:
                res.append(owd)
    else:   # only retran packet
        if False:    #tp.appParam.protocol=="INTCP"
            for owd in thrps:
                if owd > retran_threshold:
                    res.append(owd)
        else:
            prev_owd = 0
            for owd in thrps:
                if owd > retran_threshold and owd > prev_owd:
                    res.append(owd)
                prev_owd = owd
    return res

# return a list
def loadOwd(filePath):
    owds = []
    with open(filePath,'r') as f:
        lines = f.readlines()
        for line in lines:
            if "owd_obs" in line:
                pos_obs = line.find("owd_obs")
                try:
                    owd = float(line[pos_obs+8:])
                    owds.append(owd)
                except:
                    continue
    return owds

def thrpAggr(thrps,interval):
    res = []
    start = 0
    end = 0
    while start<len(thrps):
        end = start+interval
        if end>len(thrps):
            end = len(thrps)
        sum = 0
        for i in range(start,end):
            sum += thrps[i]
        sum /= (end-start)
        res.append(sum)
        start = end
    return res

#return a list
def loadThrp(filePath):
    thrps = []
    traffic_before_send = 0
    traffic_after_send = 0
    with open(filePath,'r') as f:
        lines = f.readlines()
        for line in lines:
            if 'bits/sec' in line:
                numString = line.split('bits/sec')[0][-7:-2]
                num = float(numString)/(1 if line.split('bits/sec')[0][-1]=='M' else 1000)
                thrps.append(num)
                #print(num)
            if 'bytes before test' in line:
                pos = line.find(":")
                traffic_before_send = float(line[pos+2:])
            if 'bytes after test' in line:
                pos = line.find(":")
                traffic_after_send = float(line[pos+2:])
    thrps = thrpAggr(thrps,5)
    return thrps,traffic_before_send,traffic_after_send

def loadLog(logPath, tpSet, isDetail=False,retranPacketOnly=False,metric="thrp"):
    result = {}
    for tp in tpSet.testParams:
        print('-----\n'+tp.name)
        logFilePath = '%s/%s.txt'%(logPath,tp.name)
        #print(tp.name)
        thrps = []
        result[tp] = thrps
        if tp.appParam.test_type=="throughputTest":
            thrps , __ , __ = loadThrp(logFilePath)

        elif tp.appParam.test_type=="throughputWithTraffic":
            thrps , traffic_before_send , traffic_after_send = loadThrp(logFilePath)
            if tp.appParam.protocol=="INTCP":
                intf_thrp = (traffic_after_send-traffic_before_send)*8/(1024*1024*(tp.appParam.sendTime+5))
            else:
                intf_thrp = (traffic_after_send-traffic_before_send)*8/(1024*1024*(tp.appParam.sendTime))
            thrps = [mean(thrps,method='all'),intf_thrp]
            print(thrps)

        elif tp.appParam.test_type=="trafficTest":
            with open(logFilePath,'r') as f:
                lines = f.readlines()
                for idx,line in enumerate(lines):
                    if idx==0:
                        flow1 = float(line)
                    elif idx==1:
                        flow2 = float(line)
                        thrps.append((flow2-flow1)/1000000)

        elif tp.appParam.test_type=="owdTest":
            owd_total,retran_threshold = getOwdTotal(tp)
            owds = loadOwd(logFilePath)
            thrps = screen_owd(owds,retranPacketOnly,owd_total,retran_threshold)

        elif tp.appParam.test_type=="owdThroughputBalance":
            if tp.appParam.protocol=="TCP" and not tp.appParam.sendq_length==0:
                continue
            if tp.appParam.protocol=="INTCP" and tp.appParam.sendq_length==0:
                continue

            owds = loadOwd(logFilePath)
            owd_total,retran_threshold = getOwdTotal(tp)
            owds = screen_owd(owds,False,owd_total,retran_threshold)

            thrpLogFilePath = '%s/%s_%s.txt'%(logPath,tp.name,"thrp")
            thrps,__,__ = loadThrp(thrpLogFilePath)
            thrps = [mean(owds,method='all'),mean(thrps,method='all')]
            #print(thrps)

        elif tp.appParam.test_type=="throughputWithOwd":
            if metric=="thrp":
                thrpLogFilePath = '%s/%s_%s.txt'%(logPath,tp.name,"thrp")
                thrps,__,__ = loadThrp(thrpLogFilePath)
            elif metric=="owd":
                thrps = loadOwd(logFilePath)
                #owd_total,retran_threshold = getOwdTotal(tp)
                #thrps = screen_owd(thrps,False,owd_total,retran_threshold)
        else:
            pass

        if isDetail or tp.appParam.test_type in ["throughputWithTraffic","owdThroughputBalance"]:
            result[tp] = thrps
            print(thrps)
        else:
            if len(thrps)>tp.appParam.sendTime:
                thrps = thrps[:tp.appParam.sendTime]
            result[tp] = mean(thrps,method='all')
            print('len=',len(thrps),'average =%.2f'%result[tp])
    return result

def getPlotParam(group, test_type="throughputTest"):
    if not test_type=="owdTest":
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
            '''
            if group[0].linksParam.defaultLP.bw==5:
                color = 'red'
            elif group[0].linksParam.defaultLP.bw==10:
                color = 'green'
            elif group[0].linksParam.defaultLP.bw==20:
                color = 'purple'
            else:
                color = 'royalblue'
            '''
        else:
            marker = 's'
            linestyle = '-'
            if group[0].appParam.e2eCC == 'hybla':
                color = 'green'
            elif group[0].appParam.e2eCC == 'cubic':
                color = 'royalblue'
            elif group[0].appParam.e2eCC == 'westwood':
                color = 'purple'
            elif group[0].appParam.e2eCC == 'bbr':
                color = 'black'
            elif group[0].appParam.e2eCC == 'pcc':
                color = 'orange'
        if group[0].appParam.midCC == 'nopep':
            marker = 'x'
        else:
            marker = 's'
    else:
        if group[0].appParam.midCC == 'nopep':
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
        for testParam in group:
            cnt = len(result[testParam])
            x += cnt*[testParam.get(keyX)]
            y += result[testParam]
        #sns.regplot(x=x,y=y,scatter_kws={'s':10},line_kws={'linewidth':1,'label':label},ci=95,x_estimator=np.mean)
        sns.regplot(x=x,y=y,scatter_kws={'s':2,'color':color,},line_kws={'linewidth':1,'label':label,'color':color},ci=95)

    elif mode==2:
        x = []
        y_mean=[]
        y_lower = []
        y_upper = []

        for testParam in group:
            y = result[testParam]
            if len(y)==0:
                continue
            cur_x = testParam.get(keyX)
            cur_y_lower = scoreatpercentile(y,5)
            cur_y_upper = scoreatpercentile(y,95)
            x.append(testParam.get(keyX))
            y_mean.append(mean(y,method='all'))
            y_lower.append(cur_y_lower)
            y_upper.append(cur_y_upper)
            plt.plot([cur_x,cur_x],[cur_y_lower,cur_y_upper],color=color)

        plt.plot(x,y_mean,label=label,color=color,marker=marker)
        plt.fill_between(x,y_mean,y_lower,color=color,alpha=alpha)
        plt.fill_between(x,y_mean,y_upper,color=color,alpha=alpha)

def plotOneFig(resultPath, result, keyX, groups, title, legends=[],test_type="throughputTest"):
    plt.figure(figsize=(8,5),dpi = 320)
    if test_type in ["throughputTest","throughputWithTraffic"]:
        plt.ylim((0,20))
    elif test_type=="trafficTest":
        plt.ylim((100,120))
    elif test_type=="owdTest":
        plt.ylim((0,1000))
    else:
        pass
    legend_font = {'size':12}#"family" : "Times New Roman",
    if len(groups)==1:
        group = groups[0]
        plt.plot([testParam.get(keyX) for testParam in group],
                 [result[testParam] for testParam in group])
    else:
        for i,group in enumerate(groups):

            color,marker,linestyle = getPlotParam(group,test_type)

            if test_type in ["throughputTest","trafficTest"]:
                plt.plot([testParam.get(keyX) for testParam in group],
                            [result[testParam] for testParam in group], label=legends[i],marker=marker,linestyle=linestyle,color=color,markersize=4,linewidth=1.5)
                #plt.legend()
            elif test_type=="throughputWithTraffic":
                plt.plot([testParam.get(keyX) for testParam in group],
                            [result[testParam][0] for testParam in group], label=legends[2*i],marker=marker,linestyle='-',color=color,markersize=4,linewidth=1.5)
                plt.plot([testParam.get(keyX) for testParam in group],
                            [result[testParam][1] for testParam in group], label=legends[2*i+1],marker=marker,linestyle='--',color=color,markersize=4,linewidth=1.5)
            else:
                drawCondfidenceCurve(group,result,keyX,legends[i],color,marker,mode=2)
                #plt.legend()
        plt.legend(frameon=True,prop=legend_font)
    plt.xlabel(groups[0][0].keyToStr(keyX),size=12) #family="Times New Roman",
    if test_type=="owdTest":
        plt.ylabel('one way delay(ms)',size=12)#family="Times New Roman",
        #plt.ylabel('error rate')
    elif test_type=="trafficTest":
        plt.ylabel('traffic(Mbyte)',size=12)
    else:       #throughput test
        plt.ylabel('throughput(Mbps)',size=12)#family="Times New Roman",
    plt.title(title,size=15)#family="Times New Roman",
    plt.yticks(size=12)#fontproperties = 'Times New Roman',
    plt.xticks(size=12)#fontproperties = 'Times New Roman',
    #plt.tight_layout()
    plt.savefig('%s/%s.png' % (resultPath, title))
    return
    
def simplify_curve_name(string):
    if "protocol=INTCP" in string:
        string = string.replace("e2eCC=cubic","")
        string = string.replace("protocol=INTCP","")
        if "midCC=pep" in string:
            string = string.replace("midCC=pep","")
            string = "hop INTCP"+ string
        elif "midCC=nopep" in string:
            string = string.replace("midCC=nopep","")
            string = "e2e INTCP"+ string
        else:
            string = "e2e INTCP"+ string
    if "protocol=TCP" in string:
        string = string.replace("protocol=TCP","")
    for tcpCC in ["cubic","reno","hybla","westwood","bbr","pcc"]:
        if "e2eCC=%s"%tcpCC in string and "midCC=%s"%tcpCC in string:
            string = string.replace("e2eCC=%s"%tcpCC,"")
            string = string.replace("midCC=%s"%tcpCC,"")
            string = tcpCC+ " split " + string
        elif "e2eCC=%s"%tcpCC in string and "midCC=nopep" in string:
            string = string.replace("e2eCC=%s"%tcpCC,"")
            string = string.replace("midCC=nopep","")
            string = tcpCC + string
    if "dynamic_isl_loss=0.05" in string:
        string = string.replace("dynamic_isl_loss=0.05","")
    return string

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
            string = simplify_curve_name(string)
            if not tpSet.tpTemplate.appParam.test_type=="throughputWithTraffic":
                legends.append(string)
            else:
                legends.append(string)
                legends.append(string+" intf")
        keyX = tpSet.keyX
        #isRttTest = tpSet.tpTemplate.appParam.isRttTest
        #isFlowTest = tpSet.tpTemplate.appParam.isFlowTest
        test_type = tpSet.tpTemplate.appParam.test_type
        #print("isFlowTest",isFlowTest)
        if test_type=="owdTest":
            title = '%s - OneWayDelay' % (keyX)
        elif test_type=="trafficTest":
            #print("fuck")
            title = '%s - Traffic' % (keyX)
            #print(title)
        elif test_type in ["throughputTest","throughputWithTraffic"]:
            title = '%s - throughput' % (keyX)
            print(title)
        else:
            pass
        if tpSet.keysPlotDiff != []:
            title += '(%s)' % (' '.join([curve[0].segToStr(seg) for seg in tpSet.keysPlotDiff]))
        plotOneFig(resultPath, mapNeToResult, keyX, curveGroup, title=title, legends=legends,test_type=test_type)

#TODO appParam.total_loss is removed now
def getCdfParam(tp):
    if tp.appParam.protocol=="INTCP":
        linestyle = '--'
    else:
        linestyle = '-'
    
    loss_dict = {0.1:"purple",0.2:"blue",0.5:"green",1:"orangered"}
    nodes_dict = {1:"blue",2:"orangered",3:"green"}
    midcc_dict = {'pep':"green",'nopep':'orangered'}
    
    color = loss_dict[tp.linksParam.defaultLP.loss]
    #color = nodes_dict[tp.topoParam.numMidNode]
    #color = midcc_dict[tp.appParam.midCC]
    return color,linestyle 
    
def drawCDF(tpSet, mapNeToResult, resultPath,retranPacketOnly=False,metric="thrp"):
    '''
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
    '''
    plt.figure(figsize=(8,5),dpi = 320)
    if metric == "owd":
        x_min = 0
        x_max = 8000
        xlabel = 'one way delay(ms)'
        if not retranPacketOnly:
            title = "cdf_owd_all"
            y_min = 0
            y_max = 1.01
        else:
            title = "cdf_owd_retran"
            y_min = 0
            y_max = 1.01

    elif metric=="thrp":
        xlabel = 'throughput(Mbps)'
        title = "cdf_throughput"
        x_min = -0.5
        x_max = 8
        y_min = 0
        y_max = 1.01

    x = np.linspace(x_min,x_max,num=500)
    plt.xlim((x_min,x_max))
    plt.ylim((y_min,y_max))
    
    keys = tpSet.keysCurveDiff
    legends = []
    for tp in tpSet.testParams:
        print(tp.name,min(mapNeToResult[tp]))
        if len(mapNeToResult[tp]) >0:
            #color,linestyle = getCdfParam(tp)
            ecdf = sm.distributions.ECDF(mapNeToResult[tp])
            y = ecdf(x)
            plt.step(x,y)
            #plt.step(x,y,linestyle=linestyle,color=color)
            #plt.legend(' '.join([tp.segToStr(key) for key in keys]))
            string = ' '.join([tp.segToStr(key) for key in keys])
            string = simplify_curve_name(string)
            legends.append(string)
    
    plt.legend(legends)
    plt.title(title)
    plt.xlabel(xlabel,size=12)
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

# for owd-thrp balance test
def drawScatterGraph(tpSet, mapNeToResult, resultPath):
    plt.figure(figsize=(8,5),dpi = 320)
    owd = []
    thrp = []
    # draw INTCP
    for tp in tpSet.testParams:
        if tp.appParam.protocol=="INTCP" and not tp.appParam.sendq_length==0:
            owd.append(mapNeToResult[tp][0])
            thrp.append(mapNeToResult[tp][1])
    plt.scatter(x=owd,y=thrp,marker='o',label="INTCP")
    # draw TCP
    owd = []
    thrp = []
    for tp in tpSet.testParams:
        if tp.appParam.protocol=="TCP" and tp.appParam.sendq_length==0:
            owd.append(mapNeToResult[tp][0])
            thrp.append(mapNeToResult[tp][1])
            #break
    plt.scatter(x=owd,y=thrp,marker='^',label="TCP")
    plt.legend(loc='best')
    title = "owd-thrp balance"
    plt.title(title)
    plt.xlabel("one-way-delay(ms)")
    plt.ylabel("throughput(Mbits/s)")
    plt.savefig('%s/%s.png' % (resultPath, title))

def anlz(tpSet, logPath, resultPath):
    os.chdir(sys.path[0])
    
    createFolder(resultPath)

    #mapNeToResult = loadLog(logPath, neSet, isDetail=False)
    #print('-----')
    #plotByGroup(tpSet, mapTpToResult, resultPath)
    if tpSet.tpTemplate.appParam.test_type in ["throughputTest","trafficTest","throughputWithTraffic"]:
        print('-----')
        if tpSet.tpTemplate.appParam.analyse_callback=="lineChart":
            mapTpToResult = loadLog(logPath, tpSet, isDetail=False)
            if tpSet.keyX == 'nokeyx':
                print('tpSet no keyX')
            else:
                plotByGroup(tpSet, mapTpToResult, resultPath)
            summaryString = '\n'.join(['%s   \t%.3f'%(tp.name,mapTpToResult[tp]) for tp in mapTpToResult])
            print(summaryString)
            writeText('%s/summary.txt'%(resultPath), summaryString)
            writeText('%s/template.txt'%(resultPath), tpSet.tpTemplate.serialize())
        elif tpSet.tpTemplate.appParam.analyse_callback=="cdf":
            mapTpToResult = loadLog(logPath, tpSet, isDetail=True)
            drawCDF(tpSet,mapTpToResult,resultPath,metric="thrp")

    elif tpSet.tpTemplate.appParam.test_type=="owdTest":
        #print('entering rtt analyse')
        
        generateLog(logPath,tpSet)
        
        # all packets cdf
        #mapTpToResult = loadLog(logPath, tpSet,isDetail=False)
        #drawCDF(tpSet,mapTpToResult,resultPath)
        #drawSeqGraph(tpSet,mapTpToResult, resultPath)
        
        # retranPacketOnly cdf
        mapTpToResult = loadLog(logPath, tpSet,isDetail=True,retranPacketOnly=True)
        drawCDF(tpSet,mapTpToResult,resultPath,retranPacketOnly = True,thrp="owd")

    elif tpSet.tpTemplate.appParam.test_type=="owdThroughputBalance":
        generateLog(logPath,tpSet)
        mapTpToResult = loadLog(logPath, tpSet)
        drawScatterGraph(tpSet, mapTpToResult, resultPath)
        #pass
    elif tpSet.tpTemplate.appParam.test_type=="throughputWithOwd":
        generateLog(logPath,tpSet)
        if tpSet.tpTemplate.appParam.analyse_callback=="cdf":
            mapTpToResult = loadLog(logPath, tpSet, isDetail=True,metric="thrp")
            drawCDF(tpSet,mapTpToResult,resultPath,metric="thrp")
            mapTpToResult = loadLog(logPath, tpSet, isDetail=True,metric="owd")
            drawCDF(tpSet,mapTpToResult,resultPath,metric="owd",retranPacketOnly=False)
        else:
            mapTpToResult = loadLog(logPath, tpSet, isDetail=False,metric="thrp")
            summaryString = '\n'.join(['%s   \t%.3f'%(tp.name,mapTpToResult[tp]) for tp in mapTpToResult])
            print(summaryString)
            mapTpToResult = loadLog(logPath, tpSet, isDetail=False,metric="owd")
            summaryString = '\n'.join(['%s   \t%.3f'%(tp.name,mapTpToResult[tp]) for tp in mapTpToResult])
            print(summaryString)
    fixOwnership(resultPath,'r')

"""
if __name__=='__main__':
    tpSetNames = ['expr']
    for sno,tpSetName in enumerate(tpSetNames):
        print('Analyzing TestParamSet (%d/%d)\n' % (sno+1,len(tpSetNames)))
        tpSet = MyParam.getTestParamSet(tpSetName)
        # netTopo = NetTopo.netTopos[neSet.neTemplate.netName]

        logPath = '%s/%s' % ('./logs', tpSetName)
        resultPath = '%s/%s' % ('./result', tpSetName)
        anlz(tpSet, logPath, resultPath)
"""
