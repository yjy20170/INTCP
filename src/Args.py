import argparse

class Args:
    
    def __init__(self,basicArgs=None,dictArgs={},**kwargs):
        if basicArgs != None:
            for key in basicArgs.__dict__:
                if key=='argsName':
                    continue
                self.__dict__[key]=basicArgs.__dict__[key]
        if dictArgs != {}:
            for key in dictArgs:
                self.__dict__[key]=dictArgs[key]
        for key in kwargs:
            self.__dict__[key]=kwargs[key]
            
        if 'argsName' not in self.__dict__:
            self.argsName = self.getArgsName()
            
    def getArgsName(self):
        return str(self.bw)+'m_'+str(self.rtt)+'ms_'+str(self.loss)+'%_'+str(self.prdItm)+'s_'+self.e2ecc+'_'+self.pepcc
    
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
