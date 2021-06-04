import NetHelper
import time

def itmThread(mn,args,threadLock):
    if args.prdItm>0:
        while threadLock.locked():
            time.sleep(args.prdTotal-args.prdItm)
            mn.configLinkStatus('s2','h2','down')
            time.sleep(args.prdItm)
            mn.configLinkStatus('s2','h2','up')
    else:
        return
      
def ipfThread(mn,args,threadLock):
    if args.pepcc!='none':
        mn.getNodeByName("pep").sendCmd('../bash/runpep '+args.pepcc)
    mn.getNodeByName("h2").sendCmd('iperf -s -p 5001 > ../logs/log_'+args.confName+'.txt')
    
    for i in range(5):
        mn.getNodeByName("h1").cmd('../bash/ipfc 2.1 '+str(args.testLen))
        time.sleep(args.testLen)
    
    threadLock.release()

basicArgs = NetHelper.Args(netname="0",confName='basic_conf',testLen=120,threads=[ipfThread,itmThread],bw=10,rtt=25,loss=0,prdTotal=20,prdItm=0)
def createArgs(basicArgs):
    argsSet = []
    rtt_range = [25,175,375,575]
    bw_range = [10,100]
    loss_range = [0,0.5,1]
    itm_range = [(2*i+1) for i in range(4)]
    for r in rtt_range:
        for l in loss_range:
            argsSet.append(NetHelper.Args(basicArgs,rtt=r,loss=l,pepcc="none"))
            argsSet.append(NetHelper.Args(basicArgs,rtt=r,loss=l,pepcc="hybla"))

    for itm in itm_range:
        argsSet.append(NetHelper.Args(basicArgs,loss=1,rtt=575,prdItm=itm,pepcc="none"))
        argsSet.append(NetHelper.Args(basicArgs,loss=1,rtt=575,prdItm=itm,pepcc="hybla"))
    return argsSet

# argsSet = createArgs(basicArgs)

argsSet = [NetHelper.Args(netname="0",confName='test_conf',testLen=40,threads=[ipfThread,itmThread],bw=10,rtt=25,loss=0,pepcc='none',prdTotal=20,prdItm=5)]
