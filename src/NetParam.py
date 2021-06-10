import threadFuncs

class NetParam:
    # segs are defined here.
    BasicVals = {
        'netName':'0', 'sendTime':120,
        'e2eCC':'hybla', 'pepCC':'nopep',
        'bw':10, 'rtt':575, 'loss':0,
        'prdTotal':20, 'prdItm':0,
        'varBw':0,
        'releaserFunc':threadFuncs.funcIperfPep,
        'funcs':[threadFuncs.funcMakeItm,threadFuncs.funcLinkUpdate]
    }
    
    Key = BasicVals.keys()
    
    Unit = {'bw':'Mbps','rtt':'ms','loss':'%','prdItm':'s','varBw':'Mbps',
            'e2eCC':'','pepCC':''}
    
    def __init__(self,**kwargs):
        for key in NetParam.Key:
            self.__dict__[key]=NetParam.BasicVals[key]
        for key in kwargs:
            self.__dict__[key]=kwargs[key]
        for key in NetParam.Key:
            assert self.__dict__.has_key(key)
        
    def segStr(self,seg):
        return seg+'='+str(self.__dict__[seg])+(NetParam.Unit[seg] if seg in NetParam.Unit else '')
        
    def __str__(self):
        return '%03dm_%03dms_%1.1f_i_%02ds_v_%02dm_%s_%s'
            %(self.bw,self.rtt,self.loss,self.prdItm,self.varBw,self.e2eCC,self.pepCC)
    
    def compare(self,netParam,mask=None):
        for key in NetParam.Key:
            if key==mask:
                continue
            if self.__dict__[key]!=netParam.__dict__[key]:
                return False
        return True

  
### special NetParam for test
netParams = [NetParam(
    sendTime=30,
    pepCC='nopep',
    varBw=3,
    loss=0,prdItm=0
)]

### regular experiment NetParams
def makeNetParams():
    print('Using regular experiment NetParams')
    netParams = []
    rtt_range = [25,175,375,575]
    bw_range = [10,100]
    loss_range = [0,0.5,1]
    itm_range = [(2*i+1) for i in range(4)]
    vs = [0,3]
    if 0:
        for r in rtt_range:
            for l in loss_range:
                netParams.append(NetParam(rtt=r,loss=l,pepCC='nopep'))
                netParams.append(NetParam(rtt=r,loss=l,pepCC='hybla'))
    
    asm = [[575,loss] for loss in loss_range] + [[rtt,0.5] for rtt in rtt_range]
    for rtt,loss in asm:
        for v,itm in [[0,0],[3,0],[0,3]]:
            netParams.append(NetParam(loss=loss,rtt=rtt,prdItm=itm,e2eCC='cubic',pepCC='nopep',varBw=v))
            netParams.append(NetParam(loss=loss,rtt=rtt,prdItm=itm,e2eCC='cubic',pepCC='cubic',varBw=v))
            netParams.append(NetParam(loss=loss,rtt=rtt,prdItm=itm,e2eCC='hybla',pepCC='nopep',varBw=v))
            netParams.append(NetParam(loss=loss,rtt=rtt,prdItm=itm,e2eCC='hybla',pepCC='hybla',varBw=v))
            
    return netParams

netParams = makeNetParams()
