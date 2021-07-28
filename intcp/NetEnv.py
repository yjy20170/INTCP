import threadFuncs

# class Seg:
#     def __init__(self,value):
#         self.value = value
#     def str(self):
#         return str(self.value)

# seg = key : value
# segs are defined here.

NormalFuncs = [threadFuncs.MakeItm, threadFuncs.LinkUpdate, threadFuncs.PepCC]  #threadFuncs.Init
LatchFuncs = [threadFuncs.Iperf,threadFuncs.RttTest]

BasicSegs = {
    'name':'null',
    'netName':'0', 'sendTime':120,
    'bw':10, 'rttSat':100, 'rttTotal':200, 'loss':0,
    'itmTotal':20, 'itmDown':0,
    'varBw':0, 'varIntv':1, 'varMethod':'random',
    'e2eCC':'hybla', 'pepCC':'nopep',
    'max_queue_size':1000,'txqueuelen':1000,
    'rttTestPacket':0
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

    if nesetName == "expr":
        neSet = NetEnvSet(nesetName, NetEnv(loss=5,sendTime=180,bw=20, varBw=0),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        #rttSats = [20,50,100,200,300]
        rttSats = [300]
        for rttSat in rttSats:
            
            #neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="hybla",pepCC=['hybla','nopep'])

    #1.1
    elif nesetName == "mot_rtt_6":
        neSet = NetEnvSet(nesetName, NetEnv(loss=0.1,sendTime=180,bw=20, varBw=0),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [20,50,100,200,300]
        for rttSat in rttSats:
            neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="hybla",pepCC=['nopep','hybla'])
    
    #1.1 new
    elif nesetName == "mot_rtt_7":
        neSet = NetEnvSet(nesetName, NetEnv(loss=0.1,sendTime=180,bw=20, varBw=0),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [20,50,100,150,200,250,300]
        for rttSat in rttSats:
            neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="hybla",pepCC=['nopep','hybla'])
            
    #2.1
    elif nesetName == 'mot_bwVar_10':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,rttTotal=150,rttSat=100,bw=20,sendTime=180,varMethod='square',varIntv=8),keyX="varBw",keysCurveDiff=["e2eCC","pepCC"])
        varBws = [0,4,8,12,16]
        for varBw in varBws:
            neSet.add(varBw=varBw,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(varBw=varBw,e2eCC="hybla",pepCC=['nopep','hybla'])
    
    #2.2
    elif nesetName == 'mot_bwVar_11':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,rttTotal=150,rttSat=100,bw=20,sendTime=180,varBw=8,varMethod='square'),keyX="varIntv",keysCurveDiff=["e2eCC","pepCC"])
        #varIntvs = [1,2,4,6,8,10]
        varIntvs = [2,4,6,8,10]
        for varIntv in varIntvs:
            neSet.add(varIntv=varIntv,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(varIntv=varIntv,e2eCC="hybla",pepCC=['nopep','hybla'])
    
    #2.1 new
    elif nesetName == 'mot_bwVar_12':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,rttTotal=150,rttSat=100,bw=20,sendTime=180,varMethod='square',varIntv=8),keyX="varBw",keysCurveDiff=["e2eCC","pepCC"])
        varBws = [0,3,6,9,12,15,18]
        for varBw in varBws:
            neSet.add(varBw=varBw,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(varBw=varBw,e2eCC="hybla",pepCC=['nopep','hybla'])
    
    #2.2 new
    elif nesetName == 'mot_bwVar_13':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,rttTotal=150,rttSat=100,bw=20,sendTime=180,varBw=15,varMethod='square'),keyX="varIntv",keysCurveDiff=["e2eCC","pepCC"])
        #varIntvs = [1,2,4,6,8,10]
        varIntvs = [2,4,6,8,10]
        #varIntvs = [2,4]
        #varIntvs = [2]
        for varIntv in varIntvs:
            neSet.add(varIntv=varIntv,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(varIntv=varIntv,e2eCC="hybla",pepCC=['nopep','hybla'])
            #neSet.add(varIntv=varIntv,e2eCC="cubic",pepCC=['cubic'])
            #neSet.add(varIntv=varIntv,e2eCC="hybla",pepCC=['nopep'])
                   
    #3.2
    elif nesetName == 'mot_itm_6':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0, rttTotal=150,rttSat=100,bw=40,sendTime=180),keyX="itmDown",keysCurveDiff=["pepCC","e2eCC"])  
        #itmDowns = [4,6,8,10,12]
        #itmDowns = [0,1,2,3,4,5,6,7,8]
        #itmDowns = [0,2,4,6,8]
        itmDowns = [0,1,2,3,4]
        itmTotal = 20
        for itmDown in itmDowns:
            
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='cubic',pepCC=['nopep','cubic']) 
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='hybla',pepCC=['nopep','hybla'])
    
    #3.1        
    elif nesetName == 'mot_itm_7':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0,rttTotal=150,rttSat=100, bw=40, e2eCC='hybla', pepCC='nopep',sendTime=180),keyX="itmTotal",keysCurveDiff=["pepCC","e2eCC"])  
        itmDown = 2
        itmTotals = [10,15,20,25,30]
        #neSet.add(itmTotal=25,itmDown=itmDown,e2eCC='cubic',pepCC=['nopep']) 
        for itmTotal in itmTotals:
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='cubic',pepCC=['nopep','cubic']) 
            neSet.add(itmTotal=itmTotal,itmDown=itmDown,e2eCC='hybla',pepCC=['nopep','hybla'])
    
    
    
    #4.1
    elif nesetName == "mot_retran_3":
        neSet = NetEnvSet(nesetName, NetEnv(loss=0.1,sendTime=180,bw=20, varBw=0),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [20,50,100,200,300]
        #rttSats = [100,200]
        for rttSat in rttSats:
            
            #neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="hybla",pepCC=['nopep','hybla'])
            
    elif nesetName == "mot_retran_4":
        neSet = NetEnvSet(nesetName, NetEnv(loss=5,sendTime=360,bw=20, varBw=0),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [20,50,100,200,300]
        #rttSats = [100,200]
        for rttSat in rttSats:
            
            #neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="hybla",pepCC=['nopep','hybla'])
    
    elif nesetName == "mot_retran_5":
        neSet = NetEnvSet(nesetName, NetEnv(loss=1,sendTime=180,bw=20, varBw=0),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [20,50,100,200,300]
        #rttSats = [100,200]
        for rttSat in rttSats:
            
            #neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="hybla",pepCC=['nopep','hybla'])
    
    elif nesetName == "mot_retran_6":
        neSet = NetEnvSet(nesetName, NetEnv(loss=0.5,sendTime=180,bw=20, varBw=0),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [20,50,100,200,300]
        #rttSats = [100,200]
        for rttSat in rttSats:
            
            #neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="hybla",pepCC=['nopep','hybla'])
    
    elif nesetName == "mot_retran_7":
        neSet = NetEnvSet(nesetName, NetEnv(loss=0.1,sendTime=180,bw=20, varBw=0),keyX="rttSat",keysCurveDiff=["e2eCC","pepCC"])
        rttSats = [20,50,100,200,300]
        #rttSats = [100,200]
        for rttSat in rttSats:
            
            #neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="cubic",pepCC=['nopep','cubic'])
            neSet.add(rttSat=rttSat,rttTotal=rttSat+50,e2eCC="hybla",pepCC=['nopep','hybla'])
    return neSet

