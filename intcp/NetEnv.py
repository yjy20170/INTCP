import threadFuncs

# class Seg:
#     def __init__(self,value):
#         self.value = value
#     def str(self):
#         return str(self.value)

# seg = key : value
# segs are defined here.
BasicSegs = {
    'name':'null',
    'netName':'0', 'sendTime':120,
    'bw':10, 'rttSat':100, 'rttTotal':200, 'loss':0.5,
    'itmTotal':20, 'itmDown':0,
    'varBw':0, 'varIntv':1, 'varMethod':'random',
    'e2eCC':'hybla', 'pepCC':'nopep',
    'releaserFunc': threadFuncs.funcIperfPep,
    'funcs': [threadFuncs.funcMakeItm, threadFuncs.funcLinkUpdate]
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
    # def plotTitle(self, keyX, curveDiffSegs):
    #     ### this is generated as plot title
    #     segsNotCommon = [keyX] + curveDiffSegs
    #     stringCommon = []
    #     for seg in ['rttTotal','rttSat','loss','itmDown','varBw','e2eCC','pepCC']:
    #         if seg not in segsNotCommon:
    #             stringCommon.append(self.segToStr(seg))
    #     return '%s - bandwidth\n%s' %(keyX, ' '.join(stringCommon))


class NetEnvSet:
    def __init__(self, nesetName, neTemplate, keyX='keyX', keysCurveDiff=[], **segs):
        self.nesetName = nesetName
        self.keyX = keyX
        self.keysCurveDiff = keysCurveDiff

        if neTemplate == None:
            self.neTemplate = NetEnv()
        else:
            self.neTemplate = neTemplate

        self.netEnvs = []
        self.add(**segs)

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


def getNetEnvSet(nesetName):
    print('Using NetEnvSet %s' % nesetName)
    neSet = None
    if nesetName == 'expr':
        # special NetEnv
        neSet = NetEnvSet(nesetName, None, netName = '1_test', sendTime=30, pepCC='nopep', varBw=0, loss=0, itmDown=0)

    elif nesetName == 'mot_bwVar_freq2':
        varIntv = [2,4,8,16] #[1,2,4,8,16,20]
        neSet = NetEnvSet(nesetName, NetEnv(loss=0, bw=6, varBw=4, varMethod='squareFreq', e2eCC='hybla'),
                          'varIntv', ['pepCC'],
                          varIntv=varIntv, pepCC=['hybla','nopep'])

    elif nesetName == 'mot_bwVar_freq':
        varIntv = [1,2,4,8,16,20]
        neSet = NetEnvSet(nesetName, NetEnv(loss=0, varMethod='squareFreq', e2eCC='hybla'),
                          'varIntv', ['pepCC'],
                          varIntv=varIntv, pepCC=['hybla','nopep'])

    elif nesetName == 'mot_bwVar_3':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0, varIntv=10, varMethod='square', e2eCC='hybla'),
                          'bw', ['pepCC'])
        maxBws = [6,8,10,14,18,22,26]
        minBw = 2
        for mab in maxBws:
            neSet.add(bw=(mab + minBw) / 2, varBw=(mab - minBw) / 2, pepCC=['nopep','hybla'])

    elif nesetName == 'mot_bwVar_2':
        neSet = NetEnvSet(nesetName, NetEnv(loss=0, bw=(26 + 2) / 2, varBw=(26 - 2) / 2, e2eCC='hybla', pepCC='nopep'),
                          varIntv=[1, 2, 4, 8])

    return neSet