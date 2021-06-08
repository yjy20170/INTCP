import time
from Args import Args
import thread
import random
import math


### thread for dynamic link args control

def generate_bw(meanbw,varbw,prd,policy):
    if policy=="random":
        new_bw = random.uniform(meanbw-varbw,meanbw+varbw)
        #print(new_bw)
        return new_bw
    else:
        cur_time = time.time()
        return meanbw+varbw*math.sin(2*math.pi*cur_time/prd)
        

def linkUpdateThread(mn,args,mainLock,atomicLock):
    print("linkUpdateThread starting...")
    if args.varBw>0:
        interval = 2
        while mainLock.locked():
            
            new_bw = generate_bw(args.bw,args.varBw,1,"random")
            
            pep = mn.getNodeByName("pep")
            s2 = mn.getNodeByName("s2")
            h2 = mn.getNodeByName("h2")
            
            atomicLock.acquire()
            conn1 = s2.connectionsTo(pep)[0]
            for intf in conn1:
                intf.config(bw=new_bw,delay=str(args.rtt/4)+"ms",loss=0)
            conn2 = s2.connectionsTo(h2)[0]
            for intf in conn2:
                intf.config(bw=new_bw,delay=str(args.rtt/4)+"ms",loss=args.loss)
            atomicLock.release()
    else:
        return
      
      
### thread for dynamic link up/down control

def itmThread(mn,args,mainLock,atomicLock):
    if args.prdItm>0:
        while mainLock.locked():
            time.sleep(args.prdTotal-args.prdItm)
            atomicLock.acquire()
            mn.configLinkStatus('s2','pep','down')
            atomicLock.release()
            time.sleep(args.prdItm)
            atomicLock.acquire()
            mn.configLinkStatus('s2','pep','up')
            atomicLock.release()
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
def ipfThread(mn,args,mainLock,atomicLock):
    #mn.getNodeByName("h2").xterm()
    #mn.getNodeByName("pep").xterm()
    #mn.getNodeByName("h1").xterm()
    print("ipfThread starting...")

    if args.pepcc != 'nopep':
        atomicLock.acquire()
        mn.getNodeByName("pep").cmd('../bash/runpep '+args.pepcc+' > ../logs/pep.txt &')
        atomicLock.release()

    atomicLock.acquire()
    mn.getNodeByName("h2").cmd('iperf3 -s -f k -i 30 --logfile ../logs/log_'+args.getArgsName()+'.txt &')
    atomicLock.release()
    for i in range(5):
        atomicLock.acquire()
        print("iperfc loop %d starting,testlen = %d..." %(i,args.testLen))
        mn.getNodeByName("h1").cmd('iperf3 -c 10.0.2.1 -f k -C '+args.e2ecc+' -t '+str(args.testLen)+' &')
        atomicLock.release()
        time.sleep(args.testLen)
        # no need to sleep too long under iperf3
        #time.sleep(10)
        
    print("ipf release lock")
    mainLock.release()
    
    

basicArgs = Args(

    netname="0",testLen=120,
    
    e2ecc='hybla', pepcc='nopep',
    bw=10, rtt=575, loss=0,
    prdTotal=20, prdItm=0,
    varBw=0,
    
    threads=[ipfThread,itmThread,linkUpdateThread]
)

  
### special args for test
argsSet = [Args(basicArgs=basicArgs,
    testLen=10,
    pepcc='hybla',
    varBw=1,
    loss=0.5,prdItm=0,
    threads=[ipfThread,itmThread,linkUpdateThread])]

### regular experiments args
def createArgs(basicArgs):
    argsSet = []
    rtt_range = [25,175,375,575]
    bw_range = [10,100]
    loss_range = [0,0.5,1]
    itm_range = [(2*i+1) for i in range(4)]
    vs = [0,3]
    if 0:
        for r in rtt_range:
            for l in loss_range:
                argsSet.append(Args(basicArgs,rtt=r,loss=l,pepcc="nopep"))
                argsSet.append(Args(basicArgs,rtt=r,loss=l,pepcc="hybla"))

    for itm in itm_range:
        for v in vs:
            argsSet.append(Args(basicArgs,loss=1,rtt=575,prdItm=itm,pepcc="nopep",varBw=v))
            argsSet.append(Args(basicArgs,loss=1,rtt=575,prdItm=itm,pepcc="hybla",varBw=v))
    return argsSet


# argsSet = createArgs(basicArgs)

