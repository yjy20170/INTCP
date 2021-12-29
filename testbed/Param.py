import copy

class Param:
    Keys = ['name']
    SegDefault = {'name':'xxx'}
    SegUnit = {}
    def __init__(self, template=None, **kwargs):
        for key in self.__class__.Keys:
            if key in kwargs:
                value = kwargs[key]
                kwargs.pop(key)
            elif template.__class__ == self.__class__:
                value = template.get(key)
            elif key in self.__class__.SegDefault:
                value = self.__class__.SegDefault[key]
            else:
                raise Exception('seg [%s] is missed.' % key)
            self.update(key, value)

        # like 'linkParams.pep-h2.bw'
        for key in kwargs:
            self.update(key, kwargs[key])
                
    def checkKey(self, key):
        if key not in self.__class__.Keys:
            print()
            raise Exception('key [%s] is undefined.' % key)

    def relocate(self, key):
        obj = self
        while '.' in key:
            [newObjStr,key] = key.split('.',1)
            if issubclass(type(obj), Param):
                obj = obj.get(newObjStr)
            elif type(obj) == dict:
                obj = obj[newObjStr]
            else:
                raise Exception('wrong key')
        return [obj,key]

    def update(self, key, value):
        if issubclass(value.__class__, Param):
            newValue = value.__class__(template = value)
        else:
            newValue = copy.deepcopy(value)

        [obj,key] = self.relocate(key)
        if issubclass(type(obj), Param):
            obj.checkKey(key)
            obj.__dict__[key] = newValue # copy.deepcopy(value)
        elif type(obj) == dict:
            obj[key] = newValue
        else:
            raise Exception('wrong key')

    def get(self, key):
        [obj,key] = self.relocate(key)
        if issubclass(type(obj), Param):
            obj.checkKey(key)
            return obj.__dict__[key]
        elif type(obj) == dict:
            return obj[key]
        else:
            raise Exception('wrong key')

    def getUnit(self,key):
        [obj,key] = self.relocate(key)
        if issubclass(type(obj), Param):
            obj.checkKey(key)
            if key not in obj.SegUnit:
                return ''
            else:
                return obj.SegUnit[key]
        else:
            raise Exception('wrong key')

    def compareKeys(self, param, keysCmp):
        for key in keysCmp:
            if self.get(key) != param.get(key):
                return False
        return True

    def serialize(self,indent=0):
        IndentSpace = '    '
        string = ''
        for key in self.__class__.Keys:
            string += IndentSpace*indent
            string += key+'\n'
            if issubclass(self.get(key).__class__, Param):
                string += self.get(key).serialize(indent+1)
            else:
                string += IndentSpace*(indent+1)
                string += '%s'%self.get(key) + '\n'
        return string

    # easy-to-read string of seg/key
    def segToStr(self, key):
        return '%s=%s%s'%(key, str(self.get(key)), self.getUnit(key))
    def keyToStr(self,key):
        return '%s(%s)'%(key, self.getUnit(key))

    def copy(self):
        return self.__class__(template=self)

class LinkParam(Param):
    Keys = ['name', 
            'bw', 'rtt', 'loss', 
            'itmTotal', 'itmDown',
            'varBw', 'varIntv', 'varMethod',
    ]
    SegDefault = {'name':'xxx',
            'bw':10, 'rtt':100, 'loss':0, #'rttTotal':200, 
            'itmTotal':20, 'itmDown':0,
            'varBw':0, 'varIntv':1, 'varMethod':'random'
    }
    SegUnit = {
            'bw': 'Mbps', 'rttSat': 'ms', 'loss': '%', 
            'itmDown': 's','itmTotal':'s', 
            'varBw': 'Mbps', 'varIntv': 's'
    }

class AbsTopoParam(Param):
    Keys = ['name',
            'nodes',
            'links'
    ]
    SegDefault = {'name':'xxx',
    }
    SegUnit = {
    }

# AppParam is defined by user
class AppParam(Param):
    Keys = ['name',
            'threads', #NOTE AppParam must include this seg
    ]
    SegDefault = {'name':'xxx'}
    SegUnit = {}
    def __init__(self, template=None, **kwargs):
        super().__init__(template=template, **kwargs)
    
    def serialize(self,indent=0):
        IndentSpace = '    '
        string = ''
        for key in self.__class__.Keys:
            string += IndentSpace*indent
            string += key+'\n'
            if key == 'threads':
                threads = self.get(key)
                for th in threads:
                    #print(th)
                    string += IndentSpace*(indent+1)
                    string += th.fname + '\n'
                continue
            if issubclass(self.get(key).__class__, Param):
                string += self.get(key).serialize(indent+1)
            else:
                string += IndentSpace*(indent+1)
                string += '%s'%self.get(key) + '\n'
        return string


class TestParam(Param):
    Keys = ['name',
            'absTopoParam',
            'linkParams',
            'appParam'
    ]
    SegDefault = {'name':'xxx'
    }
    SegUnit = {
    }
    def serialize(self,indent=0):
        IndentSpace = '    '
        string = ''
        for key in self.__class__.Keys:
            string += IndentSpace*indent
            string += key+'\n'
            if key == 'linkParams':
                lparams = self.get(key)
                for lp in lparams:
                    string += IndentSpace*(indent+1)
                    string += '%s:\n%s'%(lp, lparams[lp].serialize(indent+2))
                continue
            if issubclass(self.get(key).__class__, Param):
                string += self.get(key).serialize(indent+1)
            else:
                string += IndentSpace*(indent+1)
                string += '%s'%self.get(key) + '\n'
        return string

    def completeKey(self,key):
        first = key.split('.',1)[0]
        if first in self.__class__.Keys:
            return key
        else:
            if first in self.absTopoParam.__class__.Keys:
                return 'absTopoParam.' + key
            elif first in self.appParam.__class__.Keys:
                return 'appParam.' + key
            else:
                return 'linkParams.' + key
    def get(self, key):
        return super().get(self.completeKey(key))
    def getUnit(self, key):
        return super().getUnit(self.completeKey(key))
    def update(self, key, value):
        return super().update(self.completeKey(key), value)
    

class TestParamSet:
    def __init__(self, tpsetName='xxx', tpTemplate=None, keyX='null', keysCurveDiff=[], keysPlotDiff=[]):
        self.tpsetName = tpsetName
        assert(tpTemplate!=None)
        self.tpTemplate = tpTemplate
        self.keyX = keyX
        self.keysCurveDiff = keysCurveDiff
        self.keysPlotDiff = keysPlotDiff

        self.testParams = []
        
    # sometimes two or more segs are variable, but we don't want a Cartesian Product
    # at this time we must add the testParams manually by this function
    def add(self, segDict):
        # maybe some value in segs is not a list
        singleSegs = {}
        for key in segDict:
            if type(segDict[key]) != list:
                singleSegs[key] = segDict[key]
        for key in singleSegs:
            segDict.pop(key)
        # finally, the rest values in segs are lists.
        # make a Cartesian Product of these lists

        pos = [0] * len(segDict)
        keys = list(segDict.keys())
        while True:
            perm = singleSegs.copy()
            neNameElems = []
            for i,key in enumerate(keys):
                perm[key] = segDict[key][pos[i]]
                if key=="absTopoParam":
                    neNameElems.append('topo_'+perm[key].name)
                elif key=="linkParams":
                    continue
                else:
                    neNameElems.append(key+'_'+str(perm[key]))
            
            neSpec = '_'.join(neNameElems)
            self.testParams.append(TestParam(template=self.tpTemplate, name=self.tpsetName + '_' + neSpec, **perm))

            if segDict=={}:
                break
            # move to next one
            ptr = len(segDict) - 1
            pos[ptr] += 1
            done = False
            while pos[ptr] == len(segDict[keys[ptr]]):
                pos[ptr] = 0
                ptr -= 1
                if ptr == -1:
                    done = True
                    break
                pos[ptr] += 1
            if done:
                break
