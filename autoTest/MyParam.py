from testbed import Param
# from testbed.AbsNetwork import *

import userThreads
from testbed.RealNetwork import splitLoss

class MyAppParam(Param.AppParam):
    Keys = ['name',
            'threads', #NOTE AppParam must include this seg
            'isManual', #NOTE AppParam must include this seg
            'e2eCC', 'midCC','protocol',
            'max_queue_size', 'txqueuelen',
            'sendTime', 'sendRound', 
            'isRttTest', 'rttTestPacket','total_loss','midNodes',
            'isPerformTest','convs'
    ]
    SegDefault = {'name':'xxx',
        'isManual':0,
        'e2eCC':'cubic', 'midCC':'nopep','protocol':'INTCP',
        'max_queue_size':1000,'txqueuelen':1000,
        'sendTime':120, 'sendRound':3, 
        'isRttTest':0, 'rttTestPacket':0,'total_loss':0,'midNodes':1,
        'isPerformTest':0,'convs':1
    }
    # 'max_queue_size' in tc rtt limit: packets https://stackoverflow.com/questions/18792347/what-does-option-limit-in-tc-netem-mean-and-do
    # txqueuelen https://github.com/vikyd/note/blob/master/ifconfig.md#txqueuelen
    SegUnit = {
        'max_queue_size':'packets','txqueuelen':'packets',
        'sendTime':'s','total_loss':'%'
    }


def getTestParamSet(tpsetName):
    print('Using TestParamSet \'%s\'' % tpsetName)

    if tpsetName == "expr":
        absTopoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=120,sendRound=1,isRttTest=1,midCC='pep')
        
        linkParams = {
                'h1-pep':Param.LinkParam(loss=5, rtt=100, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=5, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep-h2.rtt',keysCurveDiff=['total_loss','protocol'],keysPlotDiff=[])
        
        losses = [0,2,5]
        for loss in losses:
            tpSet.add({
                'total_loss':[loss],
                'h1-pep.loss':splitLoss(loss,2),
                'pep-h2.loss':splitLoss(loss,2),
                'protocol':["INTCP","TCP"]
            })
        #tpSet.add({
        #    'pep-h2.rtt':[100,200]
        #})
        return tpSet

    if tpsetName == "expr2":
        total_loss = 5
        absTopoParam2 = Param.AbsTopoParam(name='net_hmmh',nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=1,midCC='pep')
        linkParams1 = {
                'h1-pep':Param.LinkParam(loss=splitLoss(total_loss,2), rtt=75, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=splitLoss(total_loss,2), rtt=75, bw=20, varBw=0)
        }
        linkParams2 = {
                'h1-pep1':Param.LinkParam(loss=splitLoss(total_loss,3), rtt=50, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=splitLoss(total_loss,3), rtt=50, bw=20, varBw=0),
                'pep2-h2':Param.LinkParam(loss=splitLoss(total_loss,3), rtt=50, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam2,linkParams=linkParams2,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['midNodes','protocol'],keysPlotDiff=[])
        '''
        tpSet.add({
            'pep2-h2.rtt':[50]
        })
        '''
        loss = 5
        protocols = ["INTCP,TCP"]
        #netName = ["net_hmh","net_hmmh"];
        
        absTopoParam1 = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        tpSet.add({'absTopoParam':[absTopoParam1],'linkParams':[linkParams1],'protocol':["INTCP","TCP"],'midNodes':1})
        tpSet.add({'absTopoParam':[absTopoParam2],'linkParams':[linkParams2],'protocol':["INTCP","TCP"],'midNodes':2})
        return tpSet
    
    if tpsetName == "loss_test":
        absTopoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=30,sendRound=1,isRttTest=1,midCC='pep')
        
        linkParams = {
                'h1-pep':Param.LinkParam(loss=2, rtt=100, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=2, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep-h2.rtt',keysCurveDiff=['protocol'],keysPlotDiff=[])
        

        tpSet.add({'protocol':['TCP']})

        return tpSet
    
    if tpsetName == "expr4":
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=30,sendRound=1,isRttTest=1,midCC='pep')
        absTopoParam_1 = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        absTopoParam_2 = Param.AbsTopoParam(name='net_hmmmh',nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])
        linkParams_1 = {
                'h1-pep':Param.LinkParam(loss=2, rtt=100, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=2, rtt=100, bw=20, varBw=0)
        }
        linkParams_2 = {
                'h1-pep1':Param.LinkParam(loss=2, rtt=100, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=2, rtt=100, bw=20, varBw=0),
                'pep2-pep3':Param.LinkParam(loss=2, rtt=100, bw=20, varBw=0),
                'pep3-h2':Param.LinkParam(loss=2, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam_1,linkParams=linkParams_1,appParam=appParam)
        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['midNodes','protocol'],keysPlotDiff=[])
        tpSet.add({'absTopoParam':absTopoParam_2,'linkParams':linkParams_2,'protocol':["INTCP","TCP"],'midNodes':[3]})
        tpSet.add({'absTopoParam':absTopoParam_1,'linkParams':linkParams_1,'protocol':["INTCP","TCP"],'midNodes':[1]})
        return tpSet
        
    if tpsetName == "intcp_split_test":
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=120,sendRound=1,isRttTest=1,protocol="INTCP")   
        absTopoParam = Param.AbsTopoParam(name='net_hmmmh',nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])
        linkParams = {
                'h1-pep1':Param.LinkParam(loss=0.2, rtt=100, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=0.2, rtt=100, bw=20, varBw=0),
                'pep2-pep3':Param.LinkParam(loss=0.2, rtt=100, bw=20, varBw=0),
                'pep3-h2':Param.LinkParam(loss=0.2, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam,linkParams=linkParams,appParam=appParam)
        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['protocol','midCC'],keysPlotDiff=[])
        tpSet.add({'protocol':["INTCP"],'midCC':["pep","nopep"]})
        tpSet.add({'protocol':["TCP"],'midCC':["nopep"]})
        return tpSet
    if tpsetName == "mid_nodes_test":
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=120,sendRound=1,isRttTest=1,midCC='pep')
        absTopoParam_1 = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        absTopoParam_2 = Param.AbsTopoParam(name='net_hmmh',nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
        absTopoParam_3 = Param.AbsTopoParam(name='net_hmmmh',nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])
        linkParams_1 = {
                'h1-pep':Param.LinkParam(loss=1, rtt=100, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=1, rtt=100, bw=20, varBw=0)
        }
        linkParams_2 = {
                'h1-pep1':Param.LinkParam(loss=1, rtt=100, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=1, rtt=100, bw=20, varBw=0),
                'pep2-h2':Param.LinkParam(loss=1, rtt=100, bw=20, varBw=0)
        }
        linkParams_3 = {
                'h1-pep1':Param.LinkParam(loss=1, rtt=100, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=1, rtt=100, bw=20, varBw=0),
                'pep2-pep3':Param.LinkParam(loss=1, rtt=100, bw=20, varBw=0),
                'pep3-h2':Param.LinkParam(loss=1, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam_1,linkParams=linkParams_1,appParam=appParam)
        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['midNodes','protocol'],keysPlotDiff=[])
        tpSet.add({'absTopoParam':absTopoParam_1,'linkParams':linkParams_1,'protocol':["INTCP","TCP"],'midNodes':[1]})
        tpSet.add({'absTopoParam':absTopoParam_2,'linkParams':linkParams_2,'protocol':["INTCP","TCP"],'midNodes':[2]})
        tpSet.add({'absTopoParam':absTopoParam_3,'linkParams':linkParams_3,'protocol':["INTCP","TCP"],'midNodes':[3]})
        return tpSet
        
    if tpsetName == "1ms_test":
        absTopoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=30,sendRound=1,isRttTest=1,midCC='pep')
        
        linkParams = {
                'h1-pep':Param.LinkParam(loss=0, rtt=100, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep-h2.rtt',keysCurveDiff=['total_loss','protocol'],keysPlotDiff=[])
        
        losses = [5]
        for loss in losses:
            tpSet.add({
                'total_loss':[loss],
                'h1-pep.loss':splitLoss(loss,2),
                'pep-h2.loss':splitLoss(loss,2),
                'protocol':["INTCP"]
            })
        return tpSet
    if tpsetName == "expr5":
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=60,sendRound=1,isRttTest=1,midCC='pep',protocol='INTCP')
        absTopoParam_1 = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        absTopoParam_2 = Param.AbsTopoParam(name='net_hmmmh',nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])
        linkParams_1 = {
                'h1-pep':Param.LinkParam(loss=0.2, rtt=1000, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0.2, rtt=1000, bw=20, varBw=0)
        }
        linkParams_2 = {
                'h1-pep1':Param.LinkParam(loss=0.5, rtt=100, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=0.5, rtt=100, bw=20, varBw=0),
                'pep2-pep3':Param.LinkParam(loss=0.5, rtt=100, bw=20, varBw=0),
                'pep3-h2':Param.LinkParam(loss=0.5, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam_2,linkParams=linkParams_2,appParam=appParam)
        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['protocol','total_loss'],keysPlotDiff=[])
        total_losses = [2,5,10]
        for total_loss in total_losses:
            tpSet.add({
                'protocol':["INTCP"],'total_loss':[total_loss],
                'h1-pep1.loss':splitLoss(total_loss,4),
                'pep1-pep2.loss':splitLoss(total_loss,4),
                'pep2-pep3.loss':splitLoss(total_loss,4),
                'pep3-h2.loss':splitLoss(total_loss,4)
            })
        '''
        total_losses = [0.2,0.4,1,2]
        for total_loss in total_losses:
            tpSet.add({'total_loss':[total_loss],'h1-pep.loss':splitLoss(total_loss,2),'pep-h2.loss':splitLoss(total_loss,2),'protocol':["INTCP","TCP"],'midCC':['pep']})
            tpSet.add({'total_loss':[total_loss],'h1-pep.loss':splitLoss(total_loss,2),'pep-h2.loss':splitLoss(total_loss,2),'protocol':["INTCP"],'midCC':['nopep']})
        '''
        #tpSet.add({'total_loss':[2],'h1-pep.loss':splitLoss(2,2),'pep-h2.loss':splitLoss(2,2),'protocol':["INTCP","TCP"],'midCC':['pep']})
        #tpSet.add({'total_loss':[2],'h1-pep.loss':splitLoss(2,2),'pep-h2.loss':splitLoss(2,2),'protocol':["TCP"],'midCC':['nopep']})
        return tpSet
