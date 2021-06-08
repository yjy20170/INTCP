import argparse

class Args:
    ArgKey = ['netname','testLen',
        'e2ecc','pepcc',
        'bw','rtt','loss',
        'prdTotal','prdItm',
        'varBw',
        'threads']
    
    ArgUnit = {'bw':'Mbps','rtt':'ms','loss':'%','prdItm':'s','varBw':'Mbps',
            'e2ecc':'','pepcc':''}
            
    def __init__(self,basicArgs=None,dictArgs={},**kwargs):
        if basicArgs != None:
            for key in self.ArgKey:
                self.__dict__[key]=basicArgs.__dict__[key]
        if dictArgs != {}:
            for key in dictArgs:
                self.__dict__[key]=dictArgs[key]
        for key in kwargs:
            self.__dict__[key]=kwargs[key]
        for key in self.ArgKey:
            assert self.__dict__.has_key(key)
                
    def getArgString(self,arg):
        return arg+'='+str(self.__dict__[arg])+self.ArgUnit[arg]
        
    def getArgsName(self):
        return str(self.bw)+'m_'+str(self.rtt)+'ms_'+str(self.loss)+'%_i_'+str(self.prdItm)+'s_v_'+str(self.varBw)+'m_'+self.e2ecc+'_'+self.pepcc
    
    def compare(self,argsB,mask=None):
        for key in self.ArgKey:
            if key==mask:
                continue
            if self.__dict__[key]!=argsB.__dict__[key]:
                return False
        return True
        
    @classmethod
    def getArgsFromCli(cls):
        parser = argparse.ArgumentParser()
        parser.add_argument('-net',type=str,default='0')
        parser.add_argument('-bw',type=int,default=-1)
        parser.add_argument('--itm', action='store_const', const=True, default=False, help='add intermittent')
        argsCli = parser.parse_args()
        #TODO
        #args = cls(xxx=argsCli.xxx)
        return args
