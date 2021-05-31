#coding=utf-8
import thread
import time
import argparse
import importlib
import os

from mininet.topo import Topo
from mininet.net import Mininet

def linkupdown(mn,endpA,endpB):
   while 1:
      time.sleep(8)
      mn.configLinkStatus(endpA,endpB,'down')
      time.sleep(2)
      mn.configLinkStatus(endpA,endpB,'up')

def createNet(setTopo,execCmd):
    
    topo=Topo()
    setTopo(topo)
    mn = Mininet(topo)
    mn.start()
    execCmd(mn)
    
    if args.itm:
        thread.start_new_thread( linkupdown, (mn, 's1', 'pep',) )
    
    mn.interact()
    
if __name__=="__main__":
    # clear
    os.system('echo "press key ↑ ↑ ↑ Enter"')

    
    parser = argparse.ArgumentParser()
    parser.add_argument('-net',type=str,default='0')
    parser.add_argument('-bw',type=int,default=-1)
    parser.add_argument('--itm', action='store_const', const=True, default=False, help='add intermittent')
    args = parser.parse_args()
    
    netpy = importlib.import_module( 'net_'+args.net )
    
    createNet(netpy.setTopo,netpy.execCmd)
