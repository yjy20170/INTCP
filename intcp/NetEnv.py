import threadFuncs

# class Seg:
#     def __init__(self,value):
#         self.value = value
#     def str(self):
#         return str(self.value)
class NetEnv:
    # seg = key : value
    # segs are defined here.
    BasicSegs = {
        'name':'null',
        'netName':'0', 'sendTime':120,
        'bw':10, 'rttSat':100, 'rttTotal':200, 'loss':0.5,
        'itmTotal':20, 'itmDown':0,
        'varBw':0, 'varIntv':1,
        'e2eCC':'hybla', 'pepCC':'nopep',
        'releaserFunc': threadFuncs.funcIperfPep,
        'funcs': [threadFuncs.funcMakeItm, threadFuncs.funcLinkUpdate]
    }

    Keys = BasicSegs.keys()
    SegUnit = {'bw': 'Mbps', 'rttSat': 'ms', 'rttTotal': 'ms', 'loss': '%', 'itmDown': 's', 'varBw': 'Mbps', 'varIntv': 's',
            'e2eCC': '', 'pepCC': ''}

    def __init__(self, neTemplate=None, **kwargs):
        for key in self.__class__.Keys:
            if key in kwargs:
                self.update(key, kwargs[key])
            elif neTemplate != None and key in neTemplate.__dict__:
                self.update(key, neTemplate.get(key))
            elif key in self.__class__.BasicSegs:
                self.update(key, self.__class__.BasicSegs[key])
            else:
                raise Exception('ERROR: object attr [%s] is missed.' % key)
        
    def segToStr(self, key):
        return key + '=' + str(self.get(key)) + (self.__class__.SegUnit[key] if key in self.__class__.SegUnit else '')

    def groupTitle(self, segX, segsDiff=[]):
        ### this is generated as plot title
        segsNotCommon = [segX]+segsDiff
        stringCommon = []
        stringDiff = []
        for seg in ['rttSat','loss','itmDown','varBw','e2eCC','pepCC']:
            if seg in segsNotCommon:
                if seg != segX:
                    stringDiff.append(seg)
            else:
                stringCommon.append(self.segToStr(seg))

        return '%s - bandwidth (%s)' %(segX, ' '.join(stringCommon)) # +'   DIFF  '+' '.join(stringDiff)

    def update(self, key, value):
        self.__dict__[key] = value

    def get(self, key):
        return self.__dict__[key]

    def compare(self, netEnv, mask=[]):
        for key in self.__class__.Keys:
            if key in ['name']+mask:
                continue
            if self.get(key) != netEnv.get(key):
                print(key,self.get(key),netEnv.get(key))
                return False
        return True

class NetEnvSet:
    def __init__(self, neTemplate, nesetName, **segs):
        self.nesetName = nesetName
        if neTemplate == None:
            self.neTemplate = NetEnv()
        else:
            self.neTemplate = neTemplate

        self.netEnvs = []
        self.add(**segs)
        print(len(self.netEnvs))

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
                    ptr += 1
                    if ptr == len(segs):
                        done = True
                        break
                    pos[ptr] += 1
                if done:
                    break

# regular experiment NetEnvs
BasicRange = {
    'bw': [10, 50, 100, 300],
    'rttSat': [20,50,80,100,120,150],
    'loss': [0, 0.3, 0.7, 1],
    'itmDown': [0, 1, 2, 3, 4],
    'varBw': [0, 1, 3, 5, 7],
    'e2eCC': ['hybla', 'cubic'],
    'pepCC': ['hybla', 'cubic', 'nopep']
}

def getNetEnvSet(nesetName):
    print('Using NetEnvSet %s' % nesetName)
    if nesetName == 'expr':
        # special NetEnv
        return NetEnvSet(None, nesetName, netName = '1_test', sendTime=30, pepCC='nopep', varBw=0, loss=0, itmDown=0)
    elif nesetName == 'mot_bwVar_3':
        neTemplate = NetEnv(loss=0, varIntv=10, e2eCC='hybla')
        neSet = NetEnvSet(neTemplate, nesetName)
        maxBws = [6,8,10,14,18,22,26]
        minBw = 2
        for mab in maxBws:
            neSet.add(bw=(mab + minBw) / 2, varBw=(mab - minBw) / 2, pepCC=['nopep','hybla'])
        return neSet
    elif nesetName == 'mot_bwVar_2':
        neTemplate = NetEnv(loss=0, bw=(26 + 2) / 2, varBw=(26 - 2) / 2, e2eCC='hybla', pepCC='nopep')
        return NetEnvSet(neTemplate, nesetName, varIntv=[1, 2, 4, 8])
    elif nesetName == 'mot_bwVar_4':
        neTemplate = NetEnv(loss=0, sendTime=120,bw=(26 + 2) / 2, varBw=(26 - 2) / 2, e2eCC='hybla', pepCC='hybla')
        return NetEnvSet(neTemplate, nesetName, varIntv=[1, 2, 4, 8,20])
    # elif nesetName == 'basic':
    #     npTemplates += [NetEnv(loss=value) for value in BasicRange['loss']]
    #     npTemplates += [NetEnv(rttTotal=value + 25, rttSat=value) for value in [25, 75, 175, 375, 575]]
    #     npTemplates += [NetEnv(itmDown=value) for value in BasicRange['itmDown']]
    #     npTemplates += [NetEnv(varBw=value) for value in BasicRange['varBw']]
    # elif nesetName == '6.17':
    #     #DEBUG ground part rtt is set to 100ms now.
    #     npTemplates += [NetEnv(rttSat=value, loss=0.5) for value in BasicRange['rttSat']]
    #     npTemplates += [NetEnv(rttSat=100, itmDown=value) for value in BasicRange['itmDown']]
    #     npTemplates += [NetEnv(rttSat=100, varBw=value) for value in BasicRange['varBw']]
    # elif nesetName == '6.18.14':
    #     npTemplates += [NetEnv(rttSat=100, loss=value) for value in BasicRange['loss']]
    # elif nesetName == '06.22.09':
    #     npTemplates += [NetEnv(rttTotal=600, rttSat=value, loss=1) for value in [100, 200, 300, 400, 500]]
    #
    # else:
    #     raise Exception('ERROR: Unknown NetEnv set nesetName')
    #
    # netParams = []
    # for npt in npTemplates:
    #     netParams += [NetEnv(npt, e2eCC='hybla', pepCC='nopep'),
    #                   NetEnv(npt, e2eCC='cubic', pepCC='nopep'),
    #                   NetEnv(npt, e2eCC='hybla', pepCC='hybla'),
    #                   NetEnv(npt, e2eCC='cubic', pepCC='cubic')
    #                   ]

