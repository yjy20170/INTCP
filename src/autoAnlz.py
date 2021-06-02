#!/usr/bin/python
#coding=utf-8

import automnArgs

import time

def timestamp():
    return time.strftime("%m-%d-%H-%M", time.localtime()) 

if __name__=="__main__":
    results = []
    for args in automnArgs.argsSet:
        print(args.confName)
        logpath = '../logs/log_'+args.confName+'.txt'
        thrps = []
        try:
            with open(logpath,"r") as f:
                lines = f.readlines()
                for line in lines:
                    if '/sec' in line:
                        numString = line[-20:].split(' ')[-2]
                        print(numString)
                        thrps.append(float(numString))
            if len(thrps)<=2:
                print('ERROR: the amount of data is too small.')
            else:
                del thrps[thrps.index(max(thrps))]
                del thrps[thrps.index(min(thrps))]
                mid = sum(thrps)/len(thrps)
                print("Average after removing max and min: "+str(mid))
                results.append(args.confName+' '+str(mid))
        except:
            print('ERROR: log doesn\'t exists.')
        
        print('')
    print(results)
    with open('../logs/summary-'+timestamp()+'.txt','w') as f:
        f.write('\r\n'.join(results))
