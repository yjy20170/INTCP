#!/usr/bin/python
#coding=utf-8

import automnArgs
from Args import Args

import time
import matplotlib.pyplot as plt

def timestamp():
    return time.strftime("%m-%d-%H-%M", time.localtime()) 
    
def loadLog(argsSet,isDetail=False):
    result = {}
    for args in argsSet:
        print(args.getArgsName())
        logpath = '../logs/log_'+args.getArgsName()+'.txt'
        thrps = []
        try:
            with open(logpath,"r") as f:
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
                results[args] = thrps
            else:
                if len(thrps)<=2:
                    print('ERROR: the amount of data is too small.')
                else:
                    del thrps[thrps.index(max(thrps))]
                    del thrps[thrps.index(min(thrps))]
                    mid = sum(thrps)/len(thrps)
                    print("Average after removing max and min: "+str(mid))
                    result[args] = mid
        except:
            print('ERROR: log doesn\'t exists.')
        
    return result
    
def plotSeq(result,xarg,xlabel,groups,title=None,legends=[]):
    plt.figure(figsize=(10,10),dpi=100)
    plt.ylim((0,12))
    if len(groups)==1:
        group = groups[0]
        plt.plot([args.__dict__[xarg] for args in group],[result[args] for args in group])
    else:
        for i,group in enumerate(groups):
            plt.plot([args.__dict__[xarg] for args in group],
                [result[args] for args in group],label=legends[i])
        plt.legend()
    plt.xlabel(xlabel)#(xarg.title()+'('+xunit+')')
    plt.ylabel('Bandwidth(Mbps)')
    if title:
        plt.title(title)
    plt.savefig('../result/'+timestamp()+('_'+title if title else '')+'.png')
    return
    
def plotByGroup(result,xarg,xlabel):
    groups = [[result.keys()[0]]]
    for args in result.keys()[1:]:
        found = False
        for group in groups:
            if args.compare(group[0],mask=xarg):
                found = True
                group.append(args)
                break
        if not found:
            groups.append([args])
    filtGroups = []
    for group in groups:
        if len(group)>=3:
            # sort
            group = sorted(group,cmp=lambda a1,a2: a1.__dict__[xarg]-a2.__dict__[xarg])
            filtGroups.append(group)
            
    # find the difference between these groups
    if len(filtGroups)>1:
        diffArgSet = []
        for arg in Args.ArgKey:
            if arg==xarg:
                continue
            argval = filtGroups[0][0].__dict__[arg]
            for group in filtGroups[1:]:
                if group[0].__dict__[arg] != argval:
                    diffArgSet.append(arg)
                    break
        legends = []
        for group in filtGroups:
            legends.append(' '.join([group[0].getArgString(arg) for arg in diffArgSet]))
        title = xarg+'-bw under different '+','.join(diffArgSet)
        plotSeq(result,xarg,xlabel,filtGroups,title=title,legends=legends)
    else:
        title = xarg+'-bw'
        plotSeq(result,xarg,xlabel,filtGroups,title=title)
            
if __name__=="__main__":
    argsSet = automnArgs.argsSet
    result = loadLog(argsSet)
        
    # make plot
    plotByGroup(result,'prdItm','intermittent(s)')
    
            
    with open('../result/summary-'+timestamp()+'.txt','w') as f:
        #TODO concat
        f.write(str(result))
