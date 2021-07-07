import threadFuncs

class NetParam:
    # segs are defined here.
    BasicVals = {
        'netName':'0', 'sendTime':60,
        'bw':10, 'rttSat':100, 'rttTotal':200, 'loss':0.5,
        'itmTotal':20, 'itmDown':0,
        'varBw':0, 'varIntv':1,
        'e2eCC':'hybla', 'pepCC':'nopep',
        'releaserFunc': threadFuncs.funcIperfPep,
        'funcs': [threadFuncs.funcMakeItm, threadFuncs.funcLinkUpdate]
    }

    Keys = BasicVals.keys()
    Unit = {'bw': 'Mbps', 'rttSat': 'ms', 'rttTotal': 'ms', 'loss': '%', 'itmDown': 's', 'varBw': 'Mbps',
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
        
    def str(self, ver='newest'):
        if ver == 'newest':
            string = '%03dm_%03dms_%03dms_%1.1f%%_i_%02ds_v_%02dm_%s_%s'\
                     % (self.bw,self.rttTotal,self.rttSat,self.loss,self.itmDown,self.varBw,self.e2eCC,self.pepCC)
        elif ver == 'newSingleRtt':
            string = '%dm_%dms_%dms_%s%%_i_%ds_v_%dm_%s_%s'\
                     % (self.bw,self.rttTotal,self.rttSat,self.loss,self.itmDown,self.varBw,self.e2eCC,self.pepCC)
        elif ver == 'old':
            string = '%dm_%dms_%s%%_i_%ds_v_%dm_%s_%s'\
                     % (self.bw,self.rttSat,self.loss,self.itmDown,self.varBw,self.e2eCC,self.pepCC)
        return string

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
                stringCommon.append(self.segStr(seg))

        return '%s - bandwidth (%s)' %(segX, ' '.join(stringCommon)) # +'   DIFF  '+' '.join(stringDiff)

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
    'rttSat': [20,50,80,100,120,150],
    'loss': [0, 0.3, 0.7, 1],
    'itmDown': [0, 1, 2, 3, 4],
    'varBw': [0, 1, 3, 5, 7],
    'e2eCC': ['hybla', 'cubic'],
    'pepCC': ['hybla', 'cubic', 'nopep']
}

def getNetParams(npsetName):
    print('Using NetParam set: %s' % npsetName)

    # special NetParam
    if npsetName == 'expr':
        netName = '1_'
        print(netName)
        netParams = [NetParam(
            netName = netName,
            sendTime=30,
            pepCC='nopep',
            varBw=0,
            loss=0, itmDown=0
        )]
        return netParams

    npTemplates = []
    if npsetName == 'basic':
        npTemplates += [NetParam(loss=value) for value in BasicRange['loss']]
        npTemplates += [NetParam(rttTotal=value+25, rttSat=value) for value in [25, 75, 175, 375, 575]]
        npTemplates += [NetParam(itmDown=value) for value in BasicRange['itmDown']]
        npTemplates += [NetParam(varBw=value) for value in BasicRange['varBw']]
    elif npsetName == '6.17':
        #DEBUG ground part rtt is set to 100ms now.
        npTemplates += [NetParam(rttSat=value,loss=0.5) for value in BasicRange['rttSat']]
        npTemplates += [NetParam(rttSat=100, itmDown=value) for value in BasicRange['itmDown']]
        npTemplates += [NetParam(rttSat=100, varBw=value) for value in BasicRange['varBw']]
    elif npsetName == '6.18.14':
        npTemplates += [NetParam(rttSat=100, loss=value) for value in BasicRange['loss']]
    elif npsetName == '06.22.09':
        npTemplates += [NetParam(rttTotal=600,rttSat=value, loss=1) for value in [100,200,300,400,500]]
    elif npsetName == 'mot_bwVar_1':
        npTemplates += [NetParam(loss=0, bw=value/2,varBw=value/2,varIntv=2) for value in [5,10,15,20,25]]
    else:
        raise Exception('ERROR: Unknown NetParam set npsetName')

    netParams = []
    for npt in npTemplates:
        netParams += [NetParam(npt, e2eCC='hybla', pepCC='hybla'),
                      NetParam(npt, e2eCC='hybla', pepCC='nopep'),
                      NetParam(npt, e2eCC='cubic', pepCC='cubic'),
                      NetParam(npt, e2eCC='cubic', pepCC='nopep')]
    return netParams
