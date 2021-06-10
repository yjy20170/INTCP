#!/usr/bin/python

import time
import matplotlib.pyplot as plt

import NetParam

def timestamp():
    return time.strftime('%m-%d-%H-%M', time.localtime()) 
    
def loadLog(netParams,isDetail=False):
    result = {}
    for netParam in netParams:
        print(netParam)
        logpath = '../logs/log_%s.txt'%netParam
        thrps = []
        try:
            with open(logpath,'r') as f:
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
                results[netParam] = thrps
            else:
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
    
def plotSeq(result,segX,xlabel,groups,title=None,legends=[]):
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
    plt.xlabel(xlabel)#(segX.title()+'('+xunit+')')
    plt.ylabel('Bandwidth(Mbps)')
    if title:
        plt.title(title)
    plt.savefig( '../result/%s%s.png'%(timestamp(),'_'+title if title else '') )
    return
    
def plotByGroup(result,segX,xlabel):
    groups = []
    for netParam in result:
        found = False
        for group in groups:
            if netParam.compare(group[0],mask=segX):
                found = True
                group.append(netParam)
                break
        if not found:
            groups.append([netParam])
    filtGroups = []
    for group in groups:
        if len(group)>=3:
            # sort
            group = sorted(group,cmp=lambda a1,a2: a1.__dict__[segX]-a2.__dict__[segX])
            filtGroups.append(group)
            
    # find the difference between these groups
    if len(filtGroups)>1:
        diffSegs = []
        for seg in NetParam.NetParam.Key:
            if seg==segX:
                continue
            segval = filtGroups[0][0].__dict__[seg]
            for group in filtGroups[1:]:
                if group[0].__dict__[seg] != segval:
                    diffSegs.append(seg)
                    break
        legends = []
        for group in filtGroups:
            legends.append(' '.join([group[0].segStr(seg) for seg in diffSegs]))
        title = '%s-bw under different %s'%(segX,','.join(diffSegs))
        plotSeq(result,segX,xlabel,filtGroups,title=title,legends=legends)
    else:
        title = '%s-bw'%segX
        plotSeq(result,segX,xlabel,filtGroups,title=title)
            
if __name__=='__main__':
    netParams = NetParam.netParams
    result = loadLog(netParams)
    
    # make plot
    plotByGroup(result,'rtt','(%)')
    
    
    with open('../result/summary-%s.txt'%timestamp(),'w') as f:
        #TODO concat
        f.write('\n'.join(['%s   \t%.3f'%(key,result[key]) for key in result]))
