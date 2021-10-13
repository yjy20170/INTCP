from testbed import Param
# from testbed.AbsNetwork import *

import userThreads

class MyAppParam(Param.AppParam):
    Keys = ['name',
            'threads', #NOTE AppParam must include this seg
            'isManual', #NOTE AppParam must include this seg
            'e2eCC', 'midCC','protocol',
            'max_queue_size', 'txqueuelen',
            'sendTime', 'sendRound', 
            'isRttTest', 'rttTestPacket'
    ]
    SegDefault = {'name':'xxx',
        'isManual':0,
        'e2eCC':'hybla', 'midCC':'nopep','protocol':'INTCP',
        'max_queue_size':1000,'txqueuelen':1000,
        'sendTime':120, 'sendRound':3, 
        'isRttTest':0, 'rttTestPacket':0
    }
    # 'max_queue_size' in tc rtt limit: packets https://stackoverflow.com/questions/18792347/what-does-option-limit-in-tc-netem-mean-and-do
    # txqueuelen https://github.com/vikyd/note/blob/master/ifconfig.md#txqueuelen
    SegUnit = {
        'max_queue_size':'packets','txqueuelen':'packets',
        'sendTime':'s'
    }


def getTestParamSet(tpsetName):
    print('Using TestParamSet \'%s\'' % tpsetName)

    if tpsetName == "expr":
        absTopoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=60,sendRound=1,isRttTest=1,midCC='pep')
        
        linkParams = {
                'h1-pep':Param.LinkParam(loss=0, rtt=100, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep-h2.rtt',keysCurveDiff=['h1-pep.loss','protocol'],keysPlotDiff=[])
        
        losses = [1,5,10]
        for loss in losses:
            tpSet.add({
                'h1-pep.loss':[loss/2],
                'pep-h2.loss':[loss/2],
                'protocol':["INTCP","TCP"]
            })
        #tpSet.add({
        #    'pep-h2.rtt':[100,200]
        #})
        return tpSet

    if tpsetName == "expr2":
        total_loss = 5
        absTopoParam2 = Param.AbsTopoParam(name='net_hmmh',nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=60,sendRound=1,isRttTest=1,midCC='pep')
        linkParams1 = {
                'h1-pep':Param.LinkParam(loss=total_loss/2, rtt=50, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=total_loss/2, rtt=100, bw=20, varBw=0)
        }
        linkParams2 = {
                'h1-pep1':Param.LinkParam(loss=total_loss/3, rtt=50, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=total_loss/3, rtt=50, bw=20, varBw=0),
                'pep2-h2':Param.LinkParam(loss=total_loss/3, rtt=50, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam2,linkParams=linkParams2,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['absTopoParam.name','protocol'],keysPlotDiff=[])
        '''
        tpSet.add({
            'pep2-h2.rtt':[50]
        })
        '''
        loss = 5
        protocols = ["INTCP,TCP"]
        #netName = ["net_hmh","net_hmmh"];
        
        absTopoParam1 = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        tpSet.add({'absTopoParam':[absTopoParam1],'linkParams':[linkParams1],'protocol':["INTCP","TCP"]})
        tpSet.add({'absTopoParam':[absTopoParam2],'linkParams':[linkParams2],'protocol':["INTCP","TCP"]})
        return tpSet
