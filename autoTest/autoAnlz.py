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
from get_trace import get_city_distance

sys.path.append(os.path.dirname(os.sys.path[0]))
from FileUtils import createFolder, fixOwnership, writeText
import MyParam


plt.rc('font',family='Times New Roman')
tick_size = 20
label_size = 24
legend_size = 24
line_width = 2.5
marker_size = 10

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
        length = int(line[p1+7:p2-1])
        time = float(line[p2+5:])
        return seq,length,time
    elif protocol=="INTCP":
        p1 = line.find("rangeStart")
        p3 = line.find("time")
        if "rangeEnd" in line:
            p2 = line.find("rangeEnd")
        else:
            p2 = p3
        rs = int(line[p1+11:p2-1])
        re = int(line[p2+9:p3-1])
        time = float(line[p3+5:])
        return rs,re-rs,time
        
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
        repeated_packets =  0
        #load sender
        with open(senderLogFilePath,"r") as f:
            lines = f.readlines()
            for idx,line in enumerate(lines):
                #if tp.appParam.dynamic and idx<1000:    #no order
                #    continue
                try:
                    if "time" in line:
                        seq,__,time = parseLine(line,tp.appParam.protocol)
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
                        seq,__,time = parseLine(line,tp.appParam.protocol)
                        if not seq in recvTimeDict.keys():
                            recvTimeDict[seq] = time
                        else:
                            #print("repeated receive",seq)
                            repeated_packets+=1
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
        print("repeated packets",repeated_packets)
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
    #thrps = thrpAggr(thrps,30)
    return thrps,traffic_before_send,traffic_after_send

def loadLinkLayerThrp(filePath):
    prev_ts = -1
    seqs = {}
    thrps = []
    current_thrp_bytes = 0
    with open(filePath,'r') as f:
        lines = f.readlines()
        for line in lines:
            try:
                seq,length,time = parseLine(line,"TCP")
                if prev_ts == -1:
                    prev_ts = time
                if seq not in seqs.keys():     #ignore repeated packets
                    seqs[seq] = 1
                    if time>prev_ts+1:
                        thrps.append(float(current_thrp_bytes)*8/1000000)
                        current_thrp_bytes = 0
                        prev_ts = time
                    current_thrp_bytes += length
            except:
                continue
    return thrps

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
                if True: #tp.appParam.protocol=="INTCP"
                    thrpLogFilePath = '%s/%s_%s.txt'%(logPath,tp.name,"thrp")
                    thrps,__,__ = loadThrp(thrpLogFilePath)
                else:
                   thrpLogFilePath = '%s/%s_%s.txt'%(logPath,tp.name,"recv")
                   thrps = loadLinkLayerThrp(thrpLogFilePath)

            elif metric=="owd":
                thrps = loadOwd(logFilePath)
                #owd_total,retran_threshold = getOwdTotal(tp)
                #thrps = screen_owd(thrps,False,owd_total,retran_threshold)
        elif tp.appParam.test_type=="fairnessTest":
            for i in range(tp.appParam.flowNum):
                thrpLogFilePath = '%s/%s_%d.txt'%(logPath,tp.name,i+1)
                thrp,__,__ = loadThrp(thrpLogFilePath)
                thrp = [0]*tp.appParam.flowIntv*i + thrp
                thrps.append(thrp)
            pass
        else:
            pass

        if isDetail or tp.appParam.test_type in ["throughputWithTraffic","owdThroughputBalance"]:
            result[tp] = thrps
            #print(thrps)
        else:
            if metric=="thrp" and len(thrps)>tp.appParam.sendTime:
                thrps = thrps[:tp.appParam.sendTime]
            result[tp] = mean(thrps,method='all')
            print('len=',len(thrps),'average =%.2f'%result[tp])
    return result

def getPlotParam(tp):
    test_type = tp.appParam.test_type
    if test_type=="owdTest":    #cdf
        if tp.appParam.protocol=='INTCP':
            linestyle = "--"
        else:
            linestyle = "-"
        loss_to_color = {0.2:'orangered',1:'royalblue',2:'green'}
        color = loss_to_color[tp.linksParam.defaultLP.loss]
        marker = 's'
    else:
        linestyle = '-'
        if tp.appParam.protocol=="INTCP":
            color = '#ff5b00'  #orangered fd8d49
            marker = 's'
        else:
            cc_to_param={'pcc':('cornflowerblue','x'),
                         'bbr':('#2ca02c','o'),
                         'westwood':('darkviolet','v'),
                         'cubic':('orange','^'),
                         'hybla':('purple','D')}
            color,marker = cc_to_param[tp.appParam.e2eCC]
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

def plotOneFig(resultPath, result, keyX, groups, title, legends=[],test_type="throughputTest",metric="thrp"):
    plt.figure(figsize=(8,5),dpi = 320)
    if test_type in ["throughputTest","throughputWithTraffic"]:
        plt.ylim((0,20))
    elif test_type=="trafficTest":
        plt.ylim((100,120))
    elif test_type=="owdTest":
        plt.ylim((0,1000))
    elif test_type=="throughputWithOwd":
        if metric=="thrp":
            plt.ylim((0,5))
        else:
            plt.ylim((0,3000))
    else:
        pass

    #legend_font = {'size':12}#"family" : "Times New Roman",
    if len(groups)==1:
        group = groups[0]
        plt.plot([testParam.get(keyX) for testParam in group],
                 [result[testParam] for testParam in group])
    else:
        for i,group in enumerate(groups):

            color,marker,linestyle = getPlotParam(group[0])

            if test_type in ["throughputTest","trafficTest"]:
                plt.plot([testParam.get(keyX) for testParam in group],
                            [result[testParam] for testParam in group], label=legends[i],marker=marker,linestyle=linestyle,color=color,markersize=marker_size,linewidth=line_width)
                #plt.legend()
            elif test_type=="throughputWithTraffic":
                plt.plot([testParam.get(keyX) for testParam in group],
                            [result[testParam][0] for testParam in group], label=legends[2*i],marker=marker,linestyle='-',color=color,markersize=marker_size,linewidth=line_width)
                plt.plot([testParam.get(keyX) for testParam in group],
                            [result[testParam][1] for testParam in group], label=legends[2*i+1],marker=marker,linestyle='--',color=color,markersize=marker_size,linewidth=line_width)
            elif test_type=="throughputWithOwd":    #distance->thrp/owd
                vals = []
                for tp in group:
                    distance = get_city_distance(tp.appParam.src,tp.appParam.dst)
                    vals.append((distance,result[tp]))
                vals = sorted(vals,key=lambda x:x[0])
                plt.plot([val[0] for val in vals],[val[1] for val in vals],label=legends[i],marker=marker,linestyle=linestyle,color=color,markersize=marker_size,linewidth=line_width)
            else:
                drawCondfidenceCurve(group,result,keyX,legends[i],color,marker,mode=2)
                #plt.legend()
        plt.legend(frameon=True,fontsize=legend_size)

    # xlabel
    if test_type=="throughputWithOwd":
        plt.xlabel("geodesic distance(km)",size=label_size)
    else:
        string = groups[0][0].keyToStr(keyX)
        string = simplify_name(None,string)
        plt.xlabel(string,size=label_size) #family="Times New Roman",

    # ylabel
    if test_type=="owdTest" or (test_type=="throughputWithOwd" and metric=="owd"):
        plt.ylabel('OWD(ms)',size=label_size)#family="Times New Roman",
    elif test_type=="trafficTest":
        plt.ylabel('Traffic(Mbyte)',size=label_size)
    else:       #throughput test
        plt.ylabel('Throughput(Mbps)',size=label_size)#family="Times New Roman",
    

    plt.grid(True)
    plt.tick_params(labelsize=tick_size)
    plt.tight_layout()
    plt.savefig('%s/%s.png' % (resultPath, title))
    plt.savefig('%s/%s.pdf' % (resultPath, title))
    return

def drawBarChart(resultPath, result, keyX, groups, title, legends=[],test_type="throughputTest",metric="thrp"):
    plt.figure(figsize=(8,5),dpi = 320)
    if metric=="thrp":
        plt.ylim((0,5.5))
    else:
        plt.ylim((0,1000))
    x = np.arange(len(groups[0]))
    total_width,n = 0.6,3   #0.6
    width = total_width/n
    #print(len(groups))
    hatches = ['//','||','--']
    for i,group in enumerate(groups):
        color,__,__ = getPlotParam(group[0])
        label = legends[i][:3]
        #print("legend_len",len(label),"*"+label+"*")
        y = [result[testParam] for testParam in group]
        if i==(len(groups)-1)/2:
            tick_label = [simplify_name(None,tp.segToStr(keyX)) for tp in group]
            plt.bar(x+i*width,y,width=width,label=label,tick_label=tick_label,color=color,hatch=hatches[i],alpha=.99)
        else:
            plt.bar(x+i*width,y,width=width,label=label,color=color,hatch=hatches[i],alpha=.99)
    ylabel = "Throughput(Mbps)" if metric=="thrp" else "OWD(ms)"
    #plt.xticks(rotation=5)
    plt.ylabel(ylabel,size=label_size)
    plt.legend(fontsize=legend_size,loc='best',handlelength=1,handletextpad=0.2,borderpad=0.2,borderaxespad=0.2)#borderpad=0.01
    plt.grid(True)
    plt.tick_params(labelsize=tick_size)
    plt.tight_layout()
    title = "city_pairs - %s"%(metric)
    plt.savefig('%s/%s.png' % (resultPath, title))
    plt.savefig('%s/%s.pdf' % (resultPath, title))
    return

def simplify_name(tp,string):
    # labels
    if tp is None:
        if 'gs1_m1.itmDown' in string:
            string = "Intermittence time(s)"
        if 'gs1_m1.varBw' in string:
            string = "Bandwidth variance(Mbps)"
        if 'defaultLP.loss' in string:
            string = "PLR(%)"
        if 'dynamic_intv' in string:
            string = "Link change interval(s)"
        if 'dst=45' in string:
            string = "Beijing-HongKong"
        if 'dst=63' in string:
            string = "Beijing-Singapore"
        if 'dst=24' in string:
            string = "Beijing-Paris"
        if 'dst=9' in string:
            string = 'Bejing-NewYork'
    # legend
    else:
        if "protocol=INTCP" in string:
            string = string.replace("e2eCC=cubic","")
            string = string.replace("protocol=INTCP","")
            if "midCC=pep" in string:
                string = string.replace("midCC=pep","")
                string = "InC"+ string
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
        if "dynamic_isl_loss=1" in string:
            string = string.replace("dynamic_isl_loss=1","")
        if "defaultLP.loss" in string:
            if "InC" in string:
                string = string.replace("defaultLP.loss","  PLR")
            else:
                string = string.replace("defaultLP.loss","PLR")

        if "westwood" in string:
            string = string.replace("westwood","Westwood")
        if "cubic" in string:
            string = string.replace("cubic","Cubic")
        if "hybla" in string:
            string = string.replace("hybla","Hybla")
        if "pcc" in string:
            string = string.replace("pcc","PCC")
        if "bbr" in string:
            string = string.replace("bbr","BBR")
        '''
        if "PER=0.2%" in string:
            #string = string.replace("PER=0.2%","BER=2x10$^{-7}$")
            string = string.replace("PER=0.2%","BER=%.1E"%(0.2/100/10000))
        if "PER=1%" in string:
            #string = string.replace("PER=0.2%","BER=2x10$^{-7}$")
            string = string.replace("PER=1%","BER=%.1E"%(1/100/10000))
        if "PER=2%" in string:
            #string = string.replace("PER=0.2%","BER=2x10$^{-7}$")
            string = string.replace("PER=2%","BER=%.1E"%(2/100/10000))
        '''
    return string

def plotByGroup(tpSet, mapNeToResult, resultPath,metric="thrp"):
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
            if not tpSet.tpTemplate.appParam.analyse_callback=="bar":
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
            string = simplify_name(curve[0],string)
            if not tpSet.tpTemplate.appParam.test_type=="throughputWithTraffic":
                legends.append(string)
            else:
                legends.append(string)
                legends.append(string+" intf")
        keyX = tpSet.keyX
        
        test_type = tpSet.tpTemplate.appParam.test_type
        
        if test_type=="owdTest":
            title = '%s - OneWayDelay' % (keyX)
        elif test_type=="trafficTest":
            #print("fuck")
            title = '%s - Traffic' % (keyX)
            #print(title)
        elif test_type in ["throughputTest","throughputWithTraffic"]:
            title = '%s - throughput' % (keyX)
            print(title)
        elif test_type=="throughputWithOwd":
            if metric=="thrp":
                title = '%s - throughput' % ("distance")
            else:
                title = '%s - OneWayDelay' % ("distance")
        else:
            pass
        if tpSet.keysPlotDiff != []:
            title += '(%s)' % (' '.join([curve[0].segToStr(seg) for seg in tpSet.keysPlotDiff]))
        if tpSet.tpTemplate.appParam.analyse_callback=="bar":
            drawBarChart(resultPath, mapNeToResult, keyX, curveGroup, title=title, legends=legends,test_type=test_type,metric=metric)
        else:
            plotOneFig(resultPath, mapNeToResult, keyX, curveGroup, title=title, legends=legends,test_type=test_type,metric=metric)


def drawCDF(tpSet, mapNeToResult, resultPath,retranPacketOnly=False,metric="thrp"):
    plt.figure(figsize=(8,5),dpi = 320)
    if metric == "owd":
        x_min = 0
        x_max = 5000
        xlabel = 'OWD(ms)'
        if not retranPacketOnly:
            title = "cdf_owd_all"
            y_min = 0
            y_max = 1.01
        else:
            title = "cdf_owd_retran"
            y_min = 0
            y_max = 1.01

    elif metric=="thrp":
        xlabel = 'Throughput(Mbps)'
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
            color,__,linestyle = getPlotParam(tp)
            ecdf = sm.distributions.ECDF(mapNeToResult[tp])
            y = ecdf(x)
            #plt.step(x,y)
            plt.step(x,y,linestyle=linestyle,color=color,linewidth=line_width)
            #plt.legend(' '.join([tp.segToStr(key) for key in keys]))
            string = ' '.join([tp.segToStr(key) for key in keys])
            string = simplify_name(tp,string)
            legends.append(string)
    
    plt.legend(legends,fontsize=legend_size)
    #plt.title(title)
    plt.xlabel(xlabel,size=label_size)
    plt.ylabel("CDF",size=label_size)
    plt.tick_params(labelsize=tick_size)
    plt.tight_layout()
    plt.grid()
    plt.savefig('%s/%s.png' % (resultPath, title))
    plt.savefig('%s/%s.pdf' % (resultPath, title))
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
    point_size = 100
    owd = []
    thrp = []
    # draw INTCP
    for tp in tpSet.testParams:
        if tp.appParam.protocol=="INTCP" and not tp.appParam.sendq_length==0:
            owd.append(mapNeToResult[tp][0])
            thrp.append(mapNeToResult[tp][1])
    plt.scatter(x=owd,y=thrp,color='orangered',marker='o',label="InC",s=point_size)

    #draw bbr
    owd = []
    thrp = []
    for tp in tpSet.testParams:
        if tp.appParam.protocol=="TCP" and tp.appParam.e2eCC=="bbr" and tp.appParam.sendq_length==0:
            owd.append(mapNeToResult[tp][0])
            thrp.append(mapNeToResult[tp][1])
            #break
    plt.scatter(x=owd,y=thrp,color="green",marker='^',label="BBR",s=point_size)

    # draw pcc
    owd = []
    thrp = []
    for tp in tpSet.testParams:
        if tp.appParam.protocol=="TCP" and tp.appParam.e2eCC=="pcc" and tp.appParam.sendq_length==0:
            owd.append(mapNeToResult[tp][0])
            thrp.append(mapNeToResult[tp][1])
            #break
    plt.scatter(x=owd,y=thrp,color="royalblue",marker='s',label="PCC",s=point_size)

    plt.legend(loc='best',fontsize=legend_size)
    title = "owd-thrp balance"
    #plt.title(title)
    plt.xlabel("OWD(ms)",size=label_size)
    plt.ylabel("Throughput(Mbps)",size=label_size)

    plt.tick_params(labelsize=tick_size)
    plt.tight_layout()
    plt.grid()
    plt.savefig('%s/%s.png' % (resultPath, title))
    plt.savefig('%s/%s.pdf' % (resultPath, title))
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
        drawCDF(tpSet,mapTpToResult,resultPath,retranPacketOnly = True,metric="owd")

    elif tpSet.tpTemplate.appParam.test_type=="owdThroughputBalance":
        generateLog(logPath,tpSet)
        mapTpToResult = loadLog(logPath, tpSet)
        drawScatterGraph(tpSet, mapTpToResult, resultPath)
        #pass
    elif tpSet.tpTemplate.appParam.test_type=="throughputWithOwd":
        generateLog(logPath,tpSet)
        if tpSet.tpTemplate.appParam.analyse_callback=="cdf":
            for metric in ["thrp","owd"]:
                mapTpToResult = loadLog(logPath, tpSet, isDetail=True,metric=metric)
                drawCDF(tpSet,mapTpToResult,resultPath,metric=metric,retranPacketOnly=False)
        elif tpSet.tpTemplate.appParam.analyse_callback=="lineChart":
            for metric in ["thrp","owd"]:
                mapTpToResult = loadLog(logPath, tpSet, isDetail=False,metric=metric)
                plotByGroup(tpSet, mapTpToResult,resultPath,metric=metric)
                summaryString = '\n'.join(['%s   \t%.3f'%(tp.name,mapTpToResult[tp]) for tp in mapTpToResult])
                print(summaryString)
                writeText('%s/summary_%s.txt'%(resultPath,metric), summaryString)
                writeText('%s/template.txt'%(resultPath), tpSet.tpTemplate.serialize())
        elif tpSet.tpTemplate.appParam.analyse_callback=="bar":
            for metric in ["thrp","owd"]:
                mapTpToResult = loadLog(logPath, tpSet, isDetail=False,metric=metric)
                plotByGroup(tpSet, mapTpToResult,resultPath,metric=metric)
    elif tpSet.tpTemplate.appParam.test_type=="fairnessTest":
        mapTpToResult = loadLog(logPath, tpSet, isDetail=True)
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
