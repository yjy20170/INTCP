from testbed.Param import *
from testbed.RealNetwork import splitLoss

class MyAppParam(AppParam):
    Keys = [
            'max_queue_size', 'txqueuelen','total_loss',
            'protocol','e2eCC', 'midCC',
            'isRttTest',
            'sendTime', 'sendRound'
    ]
    SegDefault = {
        'e2eCC':'cubic', 'midCC':'nopep','protocol':'INTCP',
        'max_queue_size':1000,'txqueuelen':1000,
        'sendTime':120, 'sendRound':3, 
        'isRttTest':0, 'total_loss':0
    }
    # 'max_queue_size' in tc rtt limit: packets https://stackoverflow.com/questions/18792347/what-does-option-limit-in-tc-netem-mean-and-do
    # txqueuelen https://github.com/vikyd/note/blob/master/ifconfig.md#txqueuelen
    SegUnit = {
        'max_queue_size':'packets','txqueuelen':'packets',
        'total_loss':'%',
        'sendTime':'s'
    }


# basic topo
topo_1_mid = AbsTopoParam(name='1_mid',numMidNode=1,nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
topo_2_mid = AbsTopoParam(name='2_mid',numMidNode=2,nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
topo_3_mid = AbsTopoParam(name='3_mid',numMidNode=3,nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])

# linkParams generator
# argLP is LinkParam list or single LinkParam
def getLinkParams(links,argLP):
    if isinstance(argLP,list):
        linkParams = argLP
    else:
        linkParams = [argLP.copy() for l in links]
    dic = {}
    for link,lp in zip(links,linkParams):
        dic[f'{link[0]}-{link[1]}'] = lp
    return dic
# example
linkParam_basic = LinkParam(loss=0, rtt=100, bw=20)
linkParams_1_mid = getLinkParams(topo_1_mid.links, linkParam_basic)

app_basic = MyAppParam(sendTime=180,sendRound=1,isRttTest=0,midCC='pep')

tp_basic = TestParam(absTopoParam=topo_1_mid,linkParams=linkParams_1_mid,appParam=app_basic)


def getTestParamSet(tpsetName):
    tpSet = None
    if tpsetName == "expr":
        tp_basic.appParam.midCC="pep" #"nopep/pep"
        tp_basic.appParam.sendTime=10

        losss = [0.1]*4
        bandwidths = [40,40,20,40]

        lpList = []
        for i in range(4):
            lpList.append(LinkParam(linkParam_basic,bw=bandwidths[i],loss=losss[i]))
        lps = getLinkParams(topo_3_mid.links, lpList)
        tpSet = TestParamSet(tpsetName,tpTemplate=tp_basic,keyX='numMidNode')
        tpSet.add({
                'absTopoParam':[topo_3_mid], # use list, so that the name of TestParam is "xxx_topo_{topoName}"
                'linkParams':lps,
        })

    return tpSet





def getTestParamSet_Old(tpsetName):
    print('Using TestParamSet \'%s\'' % tpsetName)

    if tpsetName == "expr":
        absTopoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=10,sendRound=1,isRttTest=0,midCC='pep',e2eCC='reno')
        
        linkParams = {
                'h1-pep':Param.LinkParam(loss=5, rtt=100, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=5, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='total_loss',keysCurveDiff=['protocol'],keysPlotDiff=[])
        losses = [0.1,0.5]
        for loss in losses:
            tpSet.add({
                'total_loss':[loss],
                'h1-pep.loss':splitLoss(loss,2),
                'pep-h2.loss':splitLoss(loss,2),
                'protocol':["TCP","INTCP"]
            })
        #tpSet.add({
        #    'pep-h2.rtt':[100,200]
        #})
        return tpSet
        
    if tpsetName == "simple_multi_nodes":
        absTopoParam2 = Param.AbsTopoParam(name='net_hmmh',nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=1,midCC='pep')
        linkParams2 = {
                'h1-pep1':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=0.0, rtt=60, bw=20, varBw=0),
                'pep2-h2':Param.LinkParam(loss=0, rtt=70, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam2,linkParams=linkParams2,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['midNodes','protocol'],keysPlotDiff=[])

        tpSet.add({'protocol':["INTCP","TCP"]})
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
    #for loss-based cc test
    if tpsetName == "cc_loss_test_1":
        absTopoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=0,midCC='pep')
        linkParams = {
                'h1-pep':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='total_loss',keysCurveDiff=['protocol','e2eCC'],keysPlotDiff=[])
        losses = [0.1,0.5,1]
        for loss in losses:
            tpSet.add({'total_loss':[loss],'pep-h2.loss':0,'pep-h2.loss':loss,'protocol':["TCP"],'e2eCC':['cubic','hybla']})
            tpSet.add({'total_loss':[loss],'pep-h2.loss':0,'pep-h2.loss':loss,'protocol':["INTCP"]})
        return tpSet
        
    if tpsetName == "cc_rtt_test_1":
        absTopoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=0,midCC='pep')
        linkParams = {
                'h1-pep':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0.1, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep-h2.rtt',keysCurveDiff=['protocol','e2eCC'],keysPlotDiff=[])
        rtts = [20,50,100,200]
        for rtt in rtts:
            tpSet.add({'pep-h2.rtt':[rtt],'protocol':["TCP"],'e2eCC':['cubic','hybla']})
            tpSet.add({'pep-h2.rtt':[rtt],'protocol':["INTCP"]})
        return tpSet
    
    if tpsetName == "cc_varbw_test_1":
        absTopoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=0,midCC='pep')
        linkParams = {
                'h1-pep':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0, rtt=100, bw=20, varBw=15,varIntv=2)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep-h2.varIntv',keysCurveDiff=['protocol','e2eCC'],keysPlotDiff=[])
        varIntvs = [2,4,6,8]
        for varIntv in varIntvs:
            tpSet.add({'pep-h2.varIntv':[varIntv],'protocol':["TCP"],'e2eCC':['cubic','hybla']})
            tpSet.add({'pep-h2.varIntv':[varIntv],'protocol':["INTCP"]})
        return tpSet
    
    if tpsetName == "cc_itm_test_1":
        absTopoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=0,midCC='pep')
        linkParams = {
                'h1-pep':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep-h2.itmDown',keysCurveDiff=['protocol','e2eCC'],keysPlotDiff=[])
        itmDowns = [0,1,2,3,4]
        for itmDown in itmDowns:
            tpSet.add({'h1-pep.itmDown':0,'pep-h2.itmDown':[itmDown],'protocol':["INTCP"]})
            tpSet.add({'h1-pep.itmDown':0,'pep-h2.itmDown':[itmDown],'protocol':["TCP"],'e2eCC':['cubic','hybla']})
        return tpSet
               
    if tpsetName == "cc_nodes_test_1":
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=0,midCC='pep')
        absTopoParam_1 = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        absTopoParam_2 = Param.AbsTopoParam(name='net_hmmh',nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
        absTopoParam_3 = Param.AbsTopoParam(name='net_hmmmh',nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])
        linkParams_1 = {
                'h1-pep':Param.LinkParam(loss=0.1, rtt=100, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0.1, rtt=100, bw=20, varBw=0)
        }
        linkParams_2 = {
                'h1-pep1':Param.LinkParam(loss=0.1, rtt=100, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=0.1, rtt=100, bw=20, varBw=0),
                'pep2-h2':Param.LinkParam(loss=0.1, rtt=100, bw=20, varBw=0)
        }
        linkParams_3 = {
                'h1-pep1':Param.LinkParam(loss=0.1, rtt=100, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=0.1, rtt=100, bw=20, varBw=0),
                'pep2-pep3':Param.LinkParam(loss=0.1, rtt=100, bw=20, varBw=0),
                'pep3-h2':Param.LinkParam(loss=0.1, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(absTopoParam=absTopoParam_1,linkParams=linkParams_1,appParam=appParam)
        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='midNodes',keysCurveDiff=['protocol','e2eCC'],keysPlotDiff=[])
        tpSet.add({'absTopoParam':absTopoParam_1,'linkParams':linkParams_1,'midNodes':[1],'protocol':["TCP"],'e2eCC':["cubic","hybla"]})
        tpSet.add({'absTopoParam':absTopoParam_1,'linkParams':linkParams_1,'midNodes':[1],'protocol':["INTCP"]})
        tpSet.add({'absTopoParam':absTopoParam_2,'linkParams':linkParams_2,'midNodes':[2],'protocol':["TCP"],'e2eCC':["cubic","hybla"]})
        tpSet.add({'absTopoParam':absTopoParam_2,'linkParams':linkParams_2,'midNodes':[2],'protocol':["INTCP"]})
        tpSet.add({'absTopoParam':absTopoParam_3,'linkParams':linkParams_3,'midNodes':[3],'protocol':["TCP"],'e2eCC':["cubic","hybla"]})
        tpSet.add({'absTopoParam':absTopoParam_3,'linkParams':linkParams_3,'midNodes':[3],'protocol':["INTCP"]})
        return tpSet
