import argparse

class Args:
    
    def __init__(self,basicArgs=None,dictArgs={},**kwargs):
        if basicArgs != None:
            for key in basicArgs.__dict__:
                if key=='confName':
                    continue
                self.__dict__[key]=basicArgs.__dict__[key]
        if dictArgs != {}:
            for key in dictArgs:
                self.__dict__[key]=dictArgs[key]
        for key in kwargs:
            self.__dict__[key]=kwargs[key]
            
        if 'confName' not in self.__dict__:
            self.confName = self.getConfName()
            
    def getConfName(self):
        return 'bw_'+str(self.bw)+'_rtt_'+str(self.rtt)+'_loss_'+str(self.loss)+'_itm_'+str(self.prdItm)+'_pepcc_'+self.pepcc
    
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
