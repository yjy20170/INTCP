import threadFuncs

class NetParam:
    # segs are defined here.
    BasicVals = {
        'netName':'0', 'sendTime':120,
        'bw':10, 'rtt':575, 'loss':0.5,
        'itmTotal':20, 'itmDown':0,
        'varBw':0, 'varIntv':1,
        'e2eCC':'hybla', 'pepCC':'nopep',
        'releaserFunc': threadFuncs.funcIperfPep,
        'funcs': [threadFuncs.funcMakeItm, threadFuncs.funcLinkUpdate]
    }

    Keys = BasicVals.keys()
    Unit = {'bw': 'Mbps', 'rtt': 'ms', 'loss': '%', 'itmDown': 's', 'varBw': 'Mbps',
            'e2eCC': '', 'pepCC': ''}
    
    def __init__(self, template=None, **kwargs):
        for key in self.__class__.Keys:
            if key in kwargs:
                self.__dict__[key] = kwargs[key]
            elif template != None and key in template.__dict__:
                self.__dict__[key] = template.__dict__[key]
            elif key in self.__class__.BasicVals:
                self.__dict__[key] = self.__class__.BasicVals[key]
            else:
                raise Exception('ERROR: object attr [%s] is missed.' % key)
        
    def segStr(self, seg):
        return seg+'='+str(self.__dict__[seg])+(self.__class__.Unit[seg] if seg in self.__class__.Unit else '')
        
    def __str__(self):
        string = '%03dm_%03dms_%1.1f%_i_%02ds_v_%02dm_%s_%s'
        stringOld = '%dm_%dms_%s%%_i_%ds_v_%dm_%s_%s'
        return stringOld % (self.bw,self.rtt,self.loss,self.itmDown,self.varBw,self.e2eCC,self.pepCC)

    def groupTitle(self, segX, segsDiff=[]):
        ### this is generated as plot title
        segsNotCommon = [segX]+segsDiff
        stringCommon = []
        stringDiff = []
        for seg in ['rtt','loss','itmDown','varBw','e2eCC','pepCC']:
            if seg in segsNotCommon:
                if seg != segX:
                    stringDiff.append(seg)
            else:
                stringCommon.append(self.segStr(seg))

        return ' '.join(stringCommon)+'   DIFF  '+' '.join(stringDiff)

    def compare(self, netParam, mask=[]):
        for key in self.__class__.Keys:
            if key in mask:
                continue
            if self.__dict__[key] != netParam.__dict__[key]:
                return False
        return True


# regular experiment NetParams
BasicRange = {
    'bw': [10, 50, 100, 300],
    'rtt': [25, 75, 175, 375, 575],
    'loss': [0, 0.5, 1],
    'itmDown': [0, 1, 2, 3, 4],
    'varBw': [0, 1, 3, 5, 7],
    'e2eCC': ['hybla', 'cubic'],
    'pepCC': ['hybla', 'cubic', 'nopep']
}

def getNetParams(name):
    print('Using NetParam set: %s' % name)

    # special NetParam
    if name == 'expr':
        netParams = [NetParam(
            sendTime=30,
            pepCC='nopep',
            varBw=0,
            loss=0, itmDown=0
        )]
        return netParams

    npTemplates = []
    if name == 'basic':
        npTemplates += [NetParam(loss=value) for value in BasicRange['loss']]
        npTemplates += [NetParam(rtt=value) for value in BasicRange['rtt']]
        npTemplates += [NetParam(itmDown=value) for value in BasicRange['itmDown']]
        npTemplates += [NetParam(varBw=value) for value in BasicRange['varBw']]
    elif name == '6.17':
        #DEBUG ground part rtt is set to 100ms now.
        npTemplates += [NetParam(rtt=value,loss=0.5) for value in [20,50,80,100,120,150]]
        npTemplates += [NetParam(rtt=100, itmDown=value) for value in BasicRange['itmDown']]
        npTemplates += [NetParam(rtt=100, varBw=value) for value in BasicRange['varBw']]
    else:
        raise Exception('ERROR: Unknown NetParam set name')

    netParams = []
    for npt in npTemplates:
        netParams += [NetParam(npt, e2eCC='cubic', pepCC='nopep'),
                      NetParam(npt, e2eCC='cubic', pepCC='cubic'),
                      NetParam(npt, e2eCC='hybla', pepCC='nopep'),
                      NetParam(npt, e2eCC='hybla', pepCC='hybla')]
    return netParams
