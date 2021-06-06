import time
from Args import Args
import thread
import random
import math

def itmThread(mn,args,threadLock):
    #print("itmThread starting...")
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

        
def ipfThread(mn,args,threadLock):


    #mn.getNodeByName("h2").xterm()
    #mn.getNodeByName("pep").xterm()
    #mn.getNodeByName("h1").xterm()
    print("ipfThread starting...")
    if args.pepcc != 'nopep':
        mn.getNodeByName("pep").cmd('../bash/runpep '+args.pepcc+' &')
    mn.getNodeByName("h2").cmd('iperf3 -s -i 1 > ../logs/log_'+args.confName+'.txt &')
    #thread.start_new_thread(mn.getNodeByName("h2").cmd, ('iperf -s -p 5001 -i 1',))
    
    for i in range(5):
        #print("1334")
        mn.getNodeByName("h1").cmd('iperf3 -c 10.0.2.1 -C '+args.e2ecc+'-t '+str(args.testLen))
        time.sleep(args.testLen)
    threadLock.release()
    
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
    interval = 0.2
    if args.varbw>0:
        while threadLock.locked():
            time.sleep(interval)
            new_bw = generate_bw(args.bw,4,1,"random")
            adjust_bandwidth(mn.getNodeByName("s2"),new_bw)
            #print("afaadga")
    else:
        return
        

argsSet = [Args(netname="0",testLen=40,threads=[ipfThread,itmThread],bw=10,rtt=575,loss=0.5,e2ecc='cubic',pepcc='nopep',prdTotal=20,prdItm=0,varbw=0),
Args(netname="0",testLen=40,threads=[ipfThread,itmThread],bw=10,rtt=575,loss=1,e2ecc='hybla',pepcc='nopep',prdTotal=20,prdItm=0,varbw=0)]

basicArgs = Args(netname="0",confName='basic_conf',testLen=120,threads=[ipfThread,itmThread,linkUpdateThread],bw=10,rtt=25,loss=0,e2ecc='hybla',prdTotal=20,prdItm=0,varbw=0)
def createArgs(basicArgs):
    argsSet = []
    rtt_range = [25,175,375,575]
    bw_range = [10,100]
    loss_range = [0,0.5,1]
    itm_range = [(2*i+1) for i in range(4)]
    for r in rtt_range:
        for l in loss_range:
            argsSet.append(Args(basicArgs,rtt=r,loss=l,pepcc="nopep"))
            argsSet.append(Args(basicArgs,rtt=r,loss=l,pepcc="hybla"))

    for itm in itm_range:
        argsSet.append(Args(basicArgs,loss=1,rtt=575,prdItm=itm,pepcc="nopep"))
        argsSet.append(Args(basicArgs,loss=1,rtt=575,prdItm=itm,pepcc="hybla"))
    return argsSet

# argsSet = createArgs(basicArgs)

