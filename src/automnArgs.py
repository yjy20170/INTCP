import time
from Args import Args
import thread
import random
import math


### thread for dynamic link args control
def adjust_bandwidth(node,new_bw):
    for intf in node.intfList():
        if intf.link: # get link that connects to interface(if any)
            intfs = [ intf.link.intf1, intf.link.intf2 ] #intfs[0] is source of link and intfs[1] is dst of link
            intfs[0].config(bw=new_bw) 
            intfs[1].config(bw=new_bw)  
             
def generate_bw(meanbw,varbw,prd,policy):
    if policy=="random":
        return random.uniform(meanbw-varbw,meanbw+varbw)
    else:
        cur_time = time.time()
        return meanbw+varbw*math.sin(2*math.pi*cur_time/prd)
        
def linkUpdateThread(mn,args,threadLock):
    #print("linkUpdatethread starting...")
    if args.varbw>0:
        interval = 0.2
        while threadLock.locked():
            time.sleep(interval)
            new_bw = generate_bw(args.bw,4,1,"random")
            adjust_bandwidth(mn.getNodeByName("s2"),new_bw)
    else:
        return
      
      
### thread for dynamic link up/down control
def itmThread(mn,args,threadLock):
    if args.prdItm>0:
        while threadLock.locked():
            time.sleep(args.prdTotal-args.prdItm)
            mn.configLinkStatus('s2','pep','down')
            time.sleep(args.prdItm)
            mn.configLinkStatus('s2','pep','up')
            '''
            time.sleep(args.prdTotal-args.prdItm)
            mn.configLinkStatus('s2','h2','down')
            time.sleep(args.prdItm)
            mn.configLinkStatus('s2','h2','up')
            mn.getNodeByName("h2").cmd("route add default gw 10.0.2.90 &")
            '''
    else:
        return

        
### thread for iperf experiments with/without PEP
def ipfThread(mn,args,threadLock):
    #mn.getNodeByName("h2").xterm()
    #mn.getNodeByName("pep").xterm()
    #mn.getNodeByName("h1").xterm()
    print("ipfThread starting...")

    if args.pepcc != 'nopep':
        mn.getNodeByName("pep").cmd('../bash/runpep '+args.pepcc+' &')

    #mn.getNodeByName("h2").cmd('iperf3 -s -i 1 > ../logs/'+args.argsName+'.txt &')
    mn.getNodeByName("h2").cmd('iperf3 -s -i 30 --logfile ../logs/log_'+args.argsName+'.txt &')
    for i in range(5):
        mn.getNodeByName("h1").cmd('iperf3 -c 10.0.2.1 -C '+args.e2ecc+' -t '+str(args.testLen))
        # time.sleep(args.testLen)
        # no need to sleep too long under iperf3
        time.sleep(10)
        

    threadLock.release()
    
    

basicArgs = Args(

    testLen=120,
    
    e2ecc='hybla', pepcc='nopep',
    bw=10, rtt=575, loss=0,
    prdTotal=20, prdItm=0,
    varbw=0,
    
    argsName='basic',
    netname="0",
    threads=[ipfThread,itmThread,linkUpdateThread]
)

  
### specified args to test someting
argsSet = [Args(basicArgs=basicArgs,
    argsName='test',
    testLen=20,
    pepcc='hybla',
    loss=0.5,prdItm=2)]

### regular experiments args
def createArgs(basicArgs):
    argsSet = []
    rtt_range = [25,175,375,575]
    bw_range = [10,100]
    loss_range = [0,0.5,1]
    itm_range = [(2*i+1) for i in range(4)]
    if 0:
        for r in rtt_range:
            for l in loss_range:
                argsSet.append(Args(basicArgs,rtt=r,loss=l,pepcc="nopep"))
                argsSet.append(Args(basicArgs,rtt=r,loss=l,pepcc="hybla"))

    for itm in itm_range:
        argsSet.append(Args(basicArgs,loss=1,rtt=575,prdItm=itm,pepcc="nopep"))
        argsSet.append(Args(basicArgs,loss=1,rtt=575,prdItm=itm,pepcc="hybla"))
    return argsSet


argsSet = createArgs(basicArgs)

