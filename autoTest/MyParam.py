from testbed.Param import *
from testbed.RealNetwork import splitLoss

SegUnit['max_queue_size']='packets'
SegUnit['txqueuelen']='packets'
SegUnit['sendTime']='s'
class MyAppParam(AppParam):
    BasicKeys = [
            # 'max_queue_size' in tc rtt limit: packets https://stackoverflow.com/questions/18792347/what-does-option-limit-in-tc-netem-mean-and-do
            # txqueuelen https://github.com/vikyd/note/blob/master/ifconfig.md#txqueuelen
            # 'max_queue_size', 'txqueuelen',
            'protocol','e2eCC', 'midCC',
            'isRttTest',
            'sendTime', 'sendRound'
    ]

def get_simple_topo(n):
	name = "%d_mid"%(n)
	numMidNode = n
	nodes = []
	links = []
	nodes.append('h1')
	for i in range(n):
		nodes.append('m%d'%(i+1))
	nodes.append('h2')
	print(nodes)
	for i in range(n+1):
		links.append([nodes[i],nodes[i+1]])
	print(links)
	return TopoParam(name=name,numMidNode=numMidNode,nodes=nodes,links=links)
	
# don't change these
#
Topo1 = TopoParam(name='1_mid',numMidNode=1,nodes=['h1','pep1','h2'],links=[['h1','pep1'],['pep1','h2']])
Topo2 = TopoParam(name='2_mid',numMidNode=2,nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
Topo3 = TopoParam(name='3_mid',numMidNode=3,nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])
#Topo20 = get_simple_topo(20)
Topo20 = Topo1
# 
DefaultLP = LinkParam(
        loss=0, rtt=100, bw=20,
        itmTotal=20, itmDown=0,
        varBw=0, varIntv=5,varMethod='square')
# 
DefaultAP = MyAppParam(
        # max_queue_size=1000,txqueuelen=1000,
        sendTime=180,sendRound=1,isRttTest=0,
        e2eCC='cubic', midCC='nopep',protocol='INTCP')


def getTestParamSet(tpsetName):
	tpSet = None
	if tpsetName == "expr1":
		tpSet = TestParamSet(tpsetName,
		        Topo1,
		        LinksParam(DefaultLP.set(varIntv=20,loss=0.1), 
		            {'h1_pep1':{'bw':20},
		            'pep1_h2':{'bw':40,'rtt':100}}),
		        DefaultAP.set(sendTime=360))
		tpSet.add(
		        {},
		        {
		        # 'bbr':{'e2eCC':'bbr','protocol':'TCP'},
		        'in_pep':{'midCC':'pep'}
		        }
		)
	if tpsetName == "expr":
		tpSet = TestParamSet(tpsetName,
		        Topo20,
		        LinksParam(DefaultLP.set(bw=20,rtt=10,loss=0.1), 
		            {}),
		        DefaultAP.set(sendTime=60),
		        keyX='defaultLP.loss',
		        keysCurveDiff=['protocol'])
		tpSet.add(
		        {'defaultLP.loss':[0.1,0,1],
		        },
		        {
		        #'in_nopep':{'midCC':'nopep'},
		        'in_pep':{'midCC':'pep','protocol':'INTCP'},
		        'cubic':{'e2eCC':'cubic','protocol':'TCP'}
		        }
		)
	if tpsetName == "bp_varbw_test_1":
		tpSet = TestParamSet(tpsetName,
			Topo1,
			LinksParam(DefaultLP.set(bw=20,loss=0,sendTime=120), 
			    {'h1_pep1':{'rtt':50,'varBw':15},
			    'pep1_h2':{'rtt':100}}),
			DefaultAP.set(sendTime=120,sendRound=1),
			keyX = 'h1_pep1.varIntv',
			keysCurveDiff=['protocol'])
		tpSet.add(
			{'h1_pep1.varIntv':[2,4,6,8,10]
			},
			{
			'in_pep':{'midCC':'pep','protocol':'INTCP'},
			'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
			#'hybla':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'}
			
			}
		)
	if tpsetName == "bp_varbw_test_2":
		tpSet = TestParamSet(tpsetName,
		        Topo1,
		        LinksParam(DefaultLP.set(bw=20,loss=0,sendTime=120), 
		            {'h1_pep1':{'rtt':50,'varIntv':8},
		            'pep1_h2':{'rtt':100}}),
		        DefaultAP.set(sendTime=120,sendRound=1),
		        keyX = 'h1_pep1.varBw',
		        keysCurveDiff=['protocol'])
		tpSet.add(
		        {'h1_pep1.varBw':[0,4,8,12,16]
		        },
		        {
		        'in_pep':{'midCC':'pep','protocol':'INTCP'},
		        'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
		        #'hybla':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'}
		        
		        }
		)
	if tpsetName == "bp_rtt_test_1":
		tpSet = TestParamSet(tpsetName,
		        Topo1,
		        LinksParam(DefaultLP.set(bw=20,loss=0,sendTime=120), 
		            {'h1_pep1':{'rtt':50},
		            'pep1_h2':{'rtt':100,'loss':0.1}}),
		        DefaultAP.set(sendTime=120,sendRound=1),
		        keyX = 'pep1_h2.rtt',
		        keysCurveDiff=['protocol','e2eCC'])
		tpSet.add(
		        {'pep1_h2.rtt':[20,50,100,150,200]#,4,6,8]
		        },
		        {
		        'in_pep':{'midCC':'pep','protocol':'INTCP'},
		        'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
		        'hybla':{'midCC':'nopep','e2eCC':'hybla','protocol':'TCP'}
		        
		        }
		)
	if tpsetName == "bp_loss_test_1":
		tpSet = TestParamSet(tpsetName,
		        Topo1,
		        LinksParam(DefaultLP.set(bw=20,loss=0,sendTime=120), 
		            {'h1_pep1':{'rtt':50},
		            'pep1_h2':{'rtt':100}}),
		        DefaultAP.set(sendTime=120,sendRound=1),
		        keyX = 'pep1_h2.loss',
		        keysCurveDiff=['protocol','e2eCC'])
		tpSet.add(
		        {'pep1_h2.loss':[0.1,0.5,1,2]#,4,6,8]
		        },
		        {
		        'in_pep':{'midCC':'pep','protocol':'INTCP'},
		        'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
		        'hybla':{'midCC':'nopep','e2eCC':'hybla','protocol':'TCP'}
		        
		        }
		)
	if tpsetName == "bp_varbw_test_3":
		tpSet = TestParamSet(tpsetName,
			Topo1,
			LinksParam(DefaultLP.set(bw=20,loss=0,sendTime=120), 
			    {'h1_pep1':{'rtt':6,'varBw':15},
			    'pep1_h2':{'rtt':6}}),
			DefaultAP.set(sendTime=120,sendRound=1),
			keyX = 'h1_pep1.varIntv',
			keysCurveDiff=['protocol'])
		tpSet.add(
			{'h1_pep1.varIntv':[2,4,6,8,10]
			},
			{
			'in_pep':{'midCC':'pep','protocol':'INTCP'},
			'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
			#'hybla':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'}
			
			}
		)
	if tpsetName == "bp_varbw_test_4":
		tpSet = TestParamSet(tpsetName,
		        Topo1,
		        LinksParam(DefaultLP.set(bw=20,loss=0,sendTime=120), 
		            {'h1_pep1':{'rtt':6,'varIntv':8},
		            'pep1_h2':{'rtt':6}}),
		        DefaultAP.set(sendTime=120,sendRound=1),
		        keyX = 'h1_pep1.varBw',
		        keysCurveDiff=['protocol'])
		tpSet.add(
		        {'h1_pep1.varBw':[0,4,8,12,16]
		        },
		        {
		        'in_pep':{'midCC':'pep','protocol':'INTCP'},
		        'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
		        #'hybla':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'}
		        
		        }
		)
	if tpsetName == "isl_loss_test_1":
		tpSet = TestParamSet(tpsetName,
		        Topo3,
		        LinksParam(DefaultLP.set(bw=20,rtt=15,sendTime=120), 
		            {'h1_pep1':{'rtt':6,'loss':0},
		            'pep3_h2':{'rtt':6,'loss':0}}),
		        DefaultAP.set(sendTime=120,sendRound=1),
		        keyX = 'defaultLP.loss',
		        keysCurveDiff=['protocol','e2eCC'])
		tpSet.add(
		        {'defaultLP.loss':[0,0.1,0.5,1,2]#,4,6,8]
		        },
		        {
		        'in_pep':{'midCC':'pep','protocol':'INTCP'},
		        'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
		        'hybla':{'midCC':'nopep','e2eCC':'hybla','protocol':'TCP'}
		        
		        }
		)
	if tpsetName == "bp_itm_test_1":
		tpSet = TestParamSet(tpsetName,
			Topo1,
			LinksParam(DefaultLP.set(rtt=6,bw=20,loss=0,sendTime=120), 
			    {'h1_pep1':{'bw':40,'itmTotal':20},
			    }),
			DefaultAP.set(sendTime=120,sendRound=1),
			keyX = 'h1_pep1.itmDown',
			keysCurveDiff=['protocol'])
		tpSet.add(
			{'h1_pep1.itmDown':[0,1,2,3,4]
			},
			{
			'in_pep':{'midCC':'pep','protocol':'INTCP'},
			'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
			#'hybla':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'}
			
			}
		)
	return tpSet





def getTestParamSet_Old(tpsetName):
    print('Using TestParamSet \'%s\'' % tpsetName)

    if tpsetName == "expr":
        topoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=10,sendRound=1,isRttTest=0,midCC='pep',e2eCC='reno')
        
        linkParams = {
                'h1-pep':Param.LinkParam(loss=5, rtt=100, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=5, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(topoParam=topoParam,linkParams=linkParams,appParam=appParam)

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
        topoParam2 = Param.AbsTopoParam(name='net_hmmh',nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=1,midCC='pep')
        linkParams2 = {
                'h1-pep1':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=0.0, rtt=60, bw=20, varBw=0),
                'pep2-h2':Param.LinkParam(loss=0, rtt=70, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(topoParam=topoParam2,linkParams=linkParams2,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['midNodes','protocol'],keysPlotDiff=[])

        tpSet.add({'protocol':["INTCP","TCP"]})
        return tpSet
        
    if tpsetName == "expr2":
        total_loss = 5
        topoParam2 = Param.AbsTopoParam(name='net_hmmh',nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
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
        tpTemplate = Param.TestParam(topoParam=topoParam2,linkParams=linkParams2,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['midNodes','protocol'],keysPlotDiff=[])
        '''
        tpSet.add({
            'pep2-h2.rtt':[50]
        })
        '''
        loss = 5
        protocols = ["INTCP,TCP"]
        #netName = ["net_hmh","net_hmmh"];
        
        topoParam1 = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        tpSet.add({'topoParam':[topoParam1],'linkParams':[linkParams1],'protocol':["INTCP","TCP"],'midNodes':1})
        tpSet.add({'topoParam':[topoParam2],'linkParams':[linkParams2],'protocol':["INTCP","TCP"],'midNodes':2})
        return tpSet
    
    if tpsetName == "loss_test":
        topoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=30,sendRound=1,isRttTest=1,midCC='pep')
        
        linkParams = {
                'h1-pep':Param.LinkParam(loss=2, rtt=100, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=2, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(topoParam=topoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep-h2.rtt',keysCurveDiff=['protocol'],keysPlotDiff=[])
        

        tpSet.add({'protocol':['TCP']})

        return tpSet
    
    if tpsetName == "expr4":
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=30,sendRound=1,isRttTest=1,midCC='pep')
        topoParam_1 = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        topoParam_2 = Param.AbsTopoParam(name='net_hmmmh',nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])
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
        tpTemplate = Param.TestParam(topoParam=topoParam_1,linkParams=linkParams_1,appParam=appParam)
        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['midNodes','protocol'],keysPlotDiff=[])
        tpSet.add({'topoParam':topoParam_2,'linkParams':linkParams_2,'protocol':["INTCP","TCP"],'midNodes':[3]})
        tpSet.add({'topoParam':topoParam_1,'linkParams':linkParams_1,'protocol':["INTCP","TCP"],'midNodes':[1]})
        return tpSet
        
    if tpsetName == "intcp_split_test":
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=120,sendRound=1,isRttTest=1,protocol="INTCP")   
        topoParam = Param.AbsTopoParam(name='net_hmmmh',nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])
        linkParams = {
                'h1-pep1':Param.LinkParam(loss=0.2, rtt=100, bw=20, varBw=0),
                'pep1-pep2':Param.LinkParam(loss=0.2, rtt=100, bw=20, varBw=0),
                'pep2-pep3':Param.LinkParam(loss=0.2, rtt=100, bw=20, varBw=0),
                'pep3-h2':Param.LinkParam(loss=0.2, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(topoParam=topoParam,linkParams=linkParams,appParam=appParam)
        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['protocol','midCC'],keysPlotDiff=[])
        tpSet.add({'protocol':["INTCP"],'midCC':["pep","nopep"]})
        tpSet.add({'protocol':["TCP"],'midCC':["nopep"]})
        return tpSet
    if tpsetName == "mid_nodes_test":
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=120,sendRound=1,isRttTest=1,midCC='pep')
        topoParam_1 = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        topoParam_2 = Param.AbsTopoParam(name='net_hmmh',nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
        topoParam_3 = Param.AbsTopoParam(name='net_hmmmh',nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])
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
        tpTemplate = Param.TestParam(topoParam=topoParam_1,linkParams=linkParams_1,appParam=appParam)
        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep2-h2.rtt',keysCurveDiff=['midNodes','protocol'],keysPlotDiff=[])
        tpSet.add({'topoParam':topoParam_1,'linkParams':linkParams_1,'protocol':["INTCP","TCP"],'midNodes':[1]})
        tpSet.add({'topoParam':topoParam_2,'linkParams':linkParams_2,'protocol':["INTCP","TCP"],'midNodes':[2]})
        tpSet.add({'topoParam':topoParam_3,'linkParams':linkParams_3,'protocol':["INTCP","TCP"],'midNodes':[3]})
        return tpSet
        
    if tpsetName == "1ms_test":
        topoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=30,sendRound=1,isRttTest=1,midCC='pep')
        
        linkParams = {
                'h1-pep':Param.LinkParam(loss=0, rtt=100, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(topoParam=topoParam,linkParams=linkParams,appParam=appParam)

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
        topoParam_1 = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        topoParam_2 = Param.AbsTopoParam(name='net_hmmmh',nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])
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
        tpTemplate = Param.TestParam(topoParam=topoParam_2,linkParams=linkParams_2,appParam=appParam)
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
        topoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=0,midCC='pep')
        linkParams = {
                'h1-pep':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(topoParam=topoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='total_loss',keysCurveDiff=['protocol','e2eCC'],keysPlotDiff=[])
        losses = [0.1,0.5,1]
        for loss in losses:
            tpSet.add({'total_loss':[loss],'pep-h2.loss':0,'pep-h2.loss':loss,'protocol':["TCP"],'e2eCC':['cubic','hybla']})
            tpSet.add({'total_loss':[loss],'pep-h2.loss':0,'pep-h2.loss':loss,'protocol':["INTCP"]})
        return tpSet
        
    if tpsetName == "cc_rtt_test_1":
        topoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=0,midCC='pep')
        linkParams = {
                'h1-pep':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0.1, rtt=100, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(topoParam=topoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep-h2.rtt',keysCurveDiff=['protocol','e2eCC'],keysPlotDiff=[])
        rtts = [20,50,100,200]
        for rtt in rtts:
            tpSet.add({'pep-h2.rtt':[rtt],'protocol':["TCP"],'e2eCC':['cubic','hybla']})
            tpSet.add({'pep-h2.rtt':[rtt],'protocol':["INTCP"]})
        return tpSet
    
    if tpsetName == "cc_varbw_test_1":
        topoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=0,midCC='pep')
        linkParams = {
                'h1-pep':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0, rtt=100, bw=20, varBw=15,varIntv=2)
        }
        tpTemplate = Param.TestParam(topoParam=topoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep-h2.varIntv',keysCurveDiff=['protocol','e2eCC'],keysPlotDiff=[])
        varIntvs = [2,4,6,8]
        for varIntv in varIntvs:
            tpSet.add({'pep-h2.varIntv':[varIntv],'protocol':["TCP"],'e2eCC':['cubic','hybla']})
            tpSet.add({'pep-h2.varIntv':[varIntv],'protocol':["INTCP"]})
        return tpSet
    
    if tpsetName == "cc_itm_test_1":
        topoParam = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=0,midCC='pep')
        linkParams = {
                'h1-pep':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0),
                'pep-h2':Param.LinkParam(loss=0, rtt=50, bw=20, varBw=0)
        }
        tpTemplate = Param.TestParam(topoParam=topoParam,linkParams=linkParams,appParam=appParam)

        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='pep-h2.itmDown',keysCurveDiff=['protocol','e2eCC'],keysPlotDiff=[])
        itmDowns = [0,1,2,3,4]
        for itmDown in itmDowns:
            tpSet.add({'h1-pep.itmDown':0,'pep-h2.itmDown':[itmDown],'protocol':["INTCP"]})
            tpSet.add({'h1-pep.itmDown':0,'pep-h2.itmDown':[itmDown],'protocol':["TCP"],'e2eCC':['cubic','hybla']})
        return tpSet
               
    if tpsetName == "cc_nodes_test_1":
        appParam = MyAppParam(name='expr',threads=userThreads.threads,sendTime=180,sendRound=1,isRttTest=0,midCC='pep')
        topoParam_1 = Param.AbsTopoParam(name='net_hmh',nodes=['h1','pep','h2'],links=[['h1','pep'],['pep','h2']])
        topoParam_2 = Param.AbsTopoParam(name='net_hmmh',nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
        topoParam_3 = Param.AbsTopoParam(name='net_hmmmh',nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])
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
        tpTemplate = Param.TestParam(topoParam=topoParam_1,linkParams=linkParams_1,appParam=appParam)
        tpSet = Param.TestParamSet(tpsetName,tpTemplate,keyX='midNodes',keysCurveDiff=['protocol','e2eCC'],keysPlotDiff=[])
        tpSet.add({'topoParam':topoParam_1,'linkParams':linkParams_1,'midNodes':[1],'protocol':["TCP"],'e2eCC':["cubic","hybla"]})
        tpSet.add({'topoParam':topoParam_1,'linkParams':linkParams_1,'midNodes':[1],'protocol':["INTCP"]})
        tpSet.add({'topoParam':topoParam_2,'linkParams':linkParams_2,'midNodes':[2],'protocol':["TCP"],'e2eCC':["cubic","hybla"]})
        tpSet.add({'topoParam':topoParam_2,'linkParams':linkParams_2,'midNodes':[2],'protocol':["INTCP"]})
        tpSet.add({'topoParam':topoParam_3,'linkParams':linkParams_3,'midNodes':[3],'protocol':["TCP"],'e2eCC':["cubic","hybla"]})
        tpSet.add({'topoParam':topoParam_3,'linkParams':linkParams_3,'midNodes':[3],'protocol':["INTCP"]})
        return tpSet
