import threadFuncs

# class Seg:
#     def __init__(self,value):
#         self.value = value
#     def str(self):
#         return str(self.value)

# seg = key : value
# segs are defined here.

LatchFunc = threadFuncs.Iperf
NormalFuncs = [threadFuncs.Init, threadFuncs.MakeItm, threadFuncs.LinkUpdate, threadFuncs.PepCC]

BasicSegs = {
    'name':'null',
    'netName':'0', 'sendTime':120,
    'bw':10, 'rttSat':100, 'rttTotal':200, 'loss':0,
    'itmTotal':20, 'itmDown':0,
    'varBw':0, 'varIntv':1, 'varMethod':'random',
    'e2eCC':'hybla', 'pepCC':'nopep',
    'max_queue_size':1000,'txqueuelen':1000
}
Keys = BasicSegs.keys()
SegUnit = {'bw': 'Mbps', 'rttSat': 'ms', 'rttTotal': 'ms', 'loss': '%', 'itmDown': 's', 'varBw': 'Mbps', 'varIntv': 's',
        'e2eCC': '', 'pepCC': ''}

class NetEnv:
    def __init__(self, neTemplate=None, **kwargs):
        for key in Keys:
            if key in kwargs:
                self.update(key, kwargs[key])
            elif neTemplate != None and key in neTemplate.__dict__:
                self.update(key, neTemplate.get(key))
            elif key in BasicSegs:
                self.update(key, BasicSegs[key])
            else:
                raise Exception('ERROR: object attr [%s] is missed.' % key)

    def update(self, key, value):
        self.__dict__[key] = value

    def get(self, key):
        return self.__dict__[key]

    def compareOnly(self, netEnv, keysCmp):
        for key in Keys:
            if key == 'name':
                continue
            if key not in keysCmp:
                continue
            if self.get(key) != netEnv.get(key):
                # print(key,self.get(key),netEnv.get(key))
                return False
        return True

    def serialize(self):
        return '\n'.join(['%15s    %s'%(key,self.get(key)) for key in Keys])

    # easy-to-read string of seg/main segs
    def segToStr(self, key):
        return key + '=' + str(self.get(key)) + (SegUnit[key] if key in SegUnit else '')
    @classmethod
    def keyToStr(cls,key):
        return key + ('(%s)'%SegUnit[key] if key in SegUnit else '')
    # def plotTitle(self, keyX, curveDiffSegs):
    #     ### this is generated as plot title
    #     segsNotCommon = [keyX] + curveDiffSegs
    #     stringCommon = []
    #     for seg in ['rttTotal','rttSat','loss','itmDown','varBw','e2eCC','pepCC']:
    #         if seg not in segsNotCommon:
    #             stringCommon.append(self.segToStr(seg))
    #     return '%s - bandwidth\n%s' %(keyX, ' '.join(stringCommon))


class NetEnvSet:
    def __init__(self, nesetName, neTemplate, keyX='null', keysCurveDiff=[], **segs):
        self.nesetName = nesetName
        self.keyX = keyX
        self.keysCurveDiff = keysCurveDiff

        if neTemplate == None:
            self.neTemplate = NetEnv()
        else:
            self.neTemplate = neTemplate

        self.netEnvs = []
        
        assert (segs == {})

    # sometimes two or more segs are variable, but we don't want a Cartesian Product
    # at this time we must add the netEnvs manually by this function
    def add(self, **segs):
        # maybe some value in segs is not a list
        singleSegs = {}
        for key in segs:
            if type(segs[key]) != list:
                singleSegs[key] = segs[key]
        for key in singleSegs:
            segs.pop(key)

        if segs != {}:
            #     self.netEnvs.append(NetEnv(neTemplate=self.neTemplate, name=nesetName))
            # else:
            # finally, the rest values in segs are lists.
            # make a Cartesian Product of these lists
            pos = [0] * len(segs)
            keys = list(segs.keys())
            while True:
                perm = singleSegs.copy()
                for i,key in enumerate(keys):
                    perm[key] = segs[key][pos[i]]
                neSpec = '_'.join([key + '_' + str(perm[key]) for key in perm])
                self.netEnvs.append(NetEnv(neTemplate=self.neTemplate, name=self.nesetName + '_' + neSpec, **perm))

                # move to next one
                ptr = len(segs) - 1
                pos[ptr] += 1
                done = False
                while pos[ptr] == len(segs[keys[ptr]]):
                    pos[ptr] = 0
                    ptr -= 1
                    if ptr == -1:
                        done = True
                        break
                    pos[ptr] += 1
                if done:
                    break
        else:
            self.netEnvs.append(NetEnv(neTemplate=self.neTemplate, name=self.nesetName + '_' + str(len(self.netEnvs)), **singleSegs))


def getNetEnvSet(nesetName):
    print('Using NetEnvSet %s' % nesetName)
    neSet = None

    if nesetName == 'expr':
        # special NetEnv
        neSet = NetEnvSet(nesetName, NetEnv(loss=0, rttTotal=150, rttSat=100, bw=20, sendTime=180, varBw=8, varMethod='square'))
        neSet.add(e2eCC="hybla", pepCC=["nopep",'hybla'])

    elif nesetName == 'yjy_mot_itm':
        neSet = NetEnvSet(nesetName,
                          NetEnv(loss=0, rttTotal=150, rttSat=100, bw=40, sendTime=180,  varMethod='square'),
                          keyX="itmDown", keysCurveDiff=["e2eCC", "pepCC"])
        itmDown= [1, 2, 3, 4, 5, 6, 7, 8]
        neSet.add(itmDown=itmDown, e2eCC="hybla", pepCC=['hybla', 'nopep'])
        neSet.add(itmDown=itmDown, e2eCC="cubic", pepCC=['cubic', 'nopep'])


    elif nesetName == 'bwVar_freq_highPulse':
        varIntv = [2,4,8,16] #[1,2,4,8,16,20]
        neSet = NetEnvSet(nesetName, NetEnv(bw=10, varBw=8, varMethod='squareHighPulse', e2eCC='hybla'),
                          'varIntv', ['pepCC'])
        neSet.add(varIntv=varIntv, pepCC=['hybla','nopep'])

    elif nesetName == 'bwVar_freq_lowPulse':
        varIntv = [2,4,8,16] #[1,2,4,8,16,20]
        neSet = NetEnvSet(nesetName, NetEnv(bw=10, varBw=8, varMethod='squareLowPulse', e2eCC='hybla'),
                          'varIntv', ['pepCC'],
                          varIntv=varIntv, pepCC=['hybla','nopep'])

    elif nesetName == 'bwVar_freq_square':
        neSet = NetEnvSet(nesetName, NetEnv(bw=(26 + 2) / 2, varBw=(26 - 2) / 2, varMethod='square', e2eCC='hybla', pepCC='nopep'),
                          varIntv=[1, 2, 4, 8])

    elif nesetName == 'bwVar_var':
        neSet = NetEnvSet(nesetName, NetEnv(varIntv=10,sendTime=10, varMethod='square', e2eCC='hybla'),
                          'bw', ['pepCC'])
        maxBws = [6,8,10,14,18,22,26]
        minBw = 2
        for mab in maxBws:
            neSet.add(bw=(mab + minBw) / 2, varBw=(mab - minBw) / 2, pepCC=['nopep','hybla'])

    
    elif nesetName == 'mot_bwVar_6':

        neSet = NetEnvSet(nesetName, NetEnv(loss=0, bw=20/2, varBw=(20 - 1) / 2,varMethod='square', e2eCC='hybla', pepCC='nopep'),keyX="varIntv",
                          varIntv=[1,2,3,4,6,8,10,12])
    
    elif nesetName == 'mot_bwVar_7':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,sendTime=60,varMethod='square',varIntv=4),keyX="bw",keysCurveDiff=["e2eCC","pepCC"])
        bws = [4,6,8,10,12]
        for bw in bws:
            neSet.add(bw=bw,varBw=bw-2,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(bw=bw,varBw=bw-2,e2eCC="hybla",pepCC=['nopep','hybla'])
    
    elif nesetName == 'mot_bwVar_8':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,bw=10,sendTime=60,varMethod='square',varIntv=8),keyX="varBw",keysCurveDiff=["e2eCC","pepCC"])
        varBws = [0,2,4,8]
        for varBw in varBws:
            #neSet.add(bw=bw,varBw=bw-2,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(varBw=varBw,e2eCC="hybla",pepCC=['nopep','hybla'])
            
    elif nesetName == 'mot_bwVar_9':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,bw=10,varBw=9,sendTime=60,varMethod='square'),keyX="varIntv",keysCurveDiff=["e2eCC","pepCC"])
        varIntvs = [1,2,4,8,20]
        for varIntv in varIntvs:
        #neSet.add(bw=bw,varBw=bw-2,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(varIntv=varIntv,e2eCC="hybla",pepCC=['nopep','hybla'])
                    
    elif nesetName == "mot_rtt_test":
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,sendTime=30,bw=60, varBw=0,rttTotal=600),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [100,200,300,400,500]
        for rttSat in rttSats:
            neSet.add(rttSat=rttSat,e2eCC="hybla",pepCC=['nopep','hybla'])
            neSet.add(rttSat=rttSat,e2eCC="reno",pepCC=['nopep','reno'])
            
    elif nesetName == "mot_rtt_1":
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,sendTime=20,bw=60, varBw=0,rttTotal=1000),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [100,300,500,700,900]
        for rttSat in rttSats:
            neSet.add(rttSat=rttSat,e2eCC="hybla",pepCC=['nopep','hybla'])
            neSet.add(rttSat=rttSat,e2eCC="reno",pepCC=['nopep','reno'])
            
    elif nesetName == "mot_rtt_2":
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,sendTime=120,bw=60, varBw=0,rttTotal=1000),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [100,300,500,700,900]
        for rttSat in rttSats:
            neSet.add(rttSat=rttSat,e2eCC="hybla",pepCC=['nopep','hybla'])
            neSet.add(rttSat=rttSat,e2eCC="reno",pepCC=['nopep','reno'])
            
    elif nesetName == "mot_rtt_3":
        neSet = NetEnvSet(nesetName, NetEnv(loss=0.5,sendTime=120,bw=60, varBw=0,rttTotal=1000),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [100,300,500,700,900]
        for rttSat in rttSats:
            neSet.add(rttSat=rttSat,e2eCC="hybla",pepCC=['nopep','hybla'])
            neSet.add(rttSat=rttSat,e2eCC="reno",pepCC=['nopep','reno'])
            
    elif nesetName == "mot_rtt_4":
        neSet = NetEnvSet(nesetName, NetEnv(loss=0.5,sendTime=60,bw=60, varBw=0),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [100,200,300,400,500]
        for rttSat in rttSats:
            neSet.add(rttSat=rttSat,rttTotal=rttSat+200,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(rttSat=rttSat,rttTotal=rttSat+200,e2eCC="reno",pepCC=['nopep','reno'])
    
    elif nesetName == "mot_rtt_test1":
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,sendTime=120,bw=60, varBw=0,rttTotal=1000),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [100,300]
        for rttSat in rttSats:
            neSet.add(rttSat=rttSat,e2eCC="reno",pepCC=['reno'])
            
    elif nesetName == "mot_buf_1":
        neSet = NetEnvSet(nesetName, NetEnv(varIntv=2,bw=20/2, varBw=(20 - 1) / 2,varMethod='square'),keyX="max_queue_size",keysCurveDiff=[])
        bufsizes = [10,100,400,700,1000]
        for bufsize in bufsizes:
            neSet.add(max_queue_size=bufsize,txqueuelen=[bufsize])
    
    elif nesetName == "mot_buf_2":
        neSet = NetEnvSet(nesetName, NetEnv(bw=20/2, varBw=(20 - 1) / 2,varMethod='square'),keyX="varIntv",keysCurveDiff=["pepCC","max_queue_size"])
        varIntvs = [1,2,4,8,20]
        for varIntv in varIntvs:
            neSet.add(varIntv=varIntv,max_queue_size=0,pepCC="hybla",txqueuelen=[0]) 
            neSet.add(varIntv=varIntv,max_queue_size=1000,pepCC="hybla",txqueuelen=[1000]) 
            neSet.add(varIntv=varIntv,max_queue_size=100,pepCC="nopep",txqueuelen=[100]) 
            neSet.add(varIntv=varIntv,max_queue_size=1000,pepCC="nopep",txqueuelen=[1000])
            neSet.add(varIntv=varIntv,max_queue_size=2000,pepCC="nopep",txqueuelen=[2000])
            neSet.add(varIntv=varIntv,max_queue_size=5000,pepCC="nopep",txqueuelen=[5000])  
             
    elif nesetName == "mot_buf_3":
        neSet = NetEnvSet(nesetName, NetEnv(bw=20/2, varBw=(20 - 1) / 2,varMethod='square'),keyX="varIntv",keysCurveDiff=["pepCC","max_queue_size"])
        varIntvs = [2,4,6]
        for varIntv in varIntvs:
            neSet.add(varIntv=varIntv,max_queue_size=10,pepCC="hybla",txqueuelen=[10]) 
            neSet.add(varIntv=varIntv,max_queue_size=1000,pepCC="hybla",txqueuelen=[1000]) 
            neSet.add(varIntv=varIntv,max_queue_size=100,pepCC="nopep",txqueuelen=[100]) 
            neSet.add(varIntv=varIntv,max_queue_size=1000,pepCC="nopep",txqueuelen=[1000])
            neSet.add(varIntv=varIntv,max_queue_size=2000,pepCC="nopep",txqueuelen=[2000])
            neSet.add(varIntv=varIntv,max_queue_size=5000,pepCC="nopep",txqueuelen=[5000]) 
            
    elif nesetName == "mot_buf_4":
        neSet = NetEnvSet(nesetName, NetEnv(bw=20/2, varBw=(20 - 1) / 2,varMethod='square'),keyX="varIntv",keysCurveDiff=["pepCC","max_queue_size"])
        varIntvs = [1,2,4,6,8,10]
        for varIntv in varIntvs:
            neSet.add(varIntv=varIntv,max_queue_size=10,pepCC="hybla",txqueuelen=[10]) 
            neSet.add(varIntv=varIntv,max_queue_size=1000,pepCC="hybla",txqueuelen=[1000]) 
            neSet.add(varIntv=varIntv,max_queue_size=100,pepCC="nopep",txqueuelen=[100]) 
            neSet.add(varIntv=varIntv,max_queue_size=1000,pepCC="nopep",txqueuelen=[1000])
            neSet.add(varIntv=varIntv,max_queue_size=5000,pepCC="nopep",txqueuelen=[5000])
            neSet.add(varIntv=varIntv,max_queue_size=10000,pepCC="nopep",txqueuelen=[10000]) 
            neSet.add(varIntv=varIntv,max_queue_size=50000,pepCC="nopep",txqueuelen=[50000])
    
    elif nesetName == "mot_buf_5":
        neSet = NetEnvSet(nesetName, NetEnv(bw=20/2, sendTime=60,varBw=(20 - 1) / 2,varMethod='square'),keyX="varIntv",keysCurveDiff=["max_queue_size","txqueuelen"])
        varIntvs = [1,2,4]
        for varIntv in varIntvs:
            neSet.add(varIntv=varIntv,max_queue_size=100,txqueuelen=[100,1000]) 
            neSet.add(varIntv=varIntv,max_queue_size=1000,txqueuelen=[100,1000]) 
    
    elif nesetName == "mot_buf_6":
        neSet = NetEnvSet(nesetName, NetEnv(bw=20/2, sendTime=60,varBw=(20 - 1) / 2,varMethod='square'),keyX="varIntv",keysCurveDiff=["max_queue_size"])
        varIntvs = [1,2,4,8]
        for varIntv in varIntvs:
            neSet.add(varIntv=varIntv,max_queue_size=[800,1000,1200,2000,5000,10000]) 
            
    elif nesetName == 'mot_itm_test':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0, bw=20, e2eCC='hybla', pepCC='nopep'),keyX="itmTotal",keysCurveDiff=["pepCC","e2eCC"])  
        itmDown = 4
        itmTotals = [10,15,20,30]
        for itmTotal in itmTotals:
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='hybla',pepCC=['hybla','nopep']) 
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='reno',pepCC=['reno','nopep'])
            
    elif nesetName == 'mot_itm_1':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0, bw=10, e2eCC='hybla', pepCC='nopep'),keyX="itmTotal",keysCurveDiff=["pepCC","e2eCC"])  
        itmDown = 4
        itmTotals = [10,15,20,30]
        for itmTotal in itmTotals:
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='hybla',pepCC=['hybla','nopep']) 
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='reno',pepCC=['reno','nopep'])  
            
    elif nesetName == 'mot_itm_2':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0, bw=10,sendTime=120),keyX="itmDown",keysCurveDiff=["pepCC","e2eCC"])  
        itmDowns = [4,6,8,10,12]
        itmTotal = 20
        for itmDown in itmDowns:
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='hybla',pepCC=['hybla','nopep']) 
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='reno',pepCC=['reno','nopep']) 
    elif nesetName == 'mot_itm_3':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0, bw=10,sendTime=120),keyX="itmDown",keysCurveDiff=["pepCC","e2eCC"])  
        itmDowns = [2,3,4,5,6]
        itmTotal = 10
        for itmDown in itmDowns:
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='hybla',pepCC=['hybla','nopep']) 
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='reno',pepCC=['reno','nopep']) 
            
    elif nesetName == 'mot_itm_4':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0, bw=20,sendTime=120),keyX="itmDown",keysCurveDiff=["pepCC","e2eCC"])  
        itmDowns = [4,6,8,10,12]
        itmTotal = 20
        for itmDown in itmDowns:
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='hybla',pepCC=['hybla','nopep']) 
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='reno',pepCC=['reno','nopep']) 
    return neSet

