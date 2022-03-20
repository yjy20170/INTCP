from testbed.Param import *
from testbed.RealNetwork import * #splitLoss
from get_trace import *

SegUnit['max_queue_size']='packets'
SegUnit['txqueuelen']='packets'
SegUnit['sendTime']='s'
SegUnit['dynamic_intv']='s'
SegUnit['sendq_length']='MSS'

class MyAppParam(AppParam):
    BasicKeys = [
            # 'max_queue_size' in tc rtt limit: packets https://stackoverflow.com/questions/18792347/what-does-option-limit-in-tc-netem-mean-and-do
            # txqueuelen https://github.com/vikyd/note/blob/master/ifconfig.md#txqueuelen
            # 'max_queue_size', 'txqueuelen',
            'protocol','e2eCC', 'midCC',
            'sendTime', 'sendRound',
            'dynamic','dynamic_intv',
            'data_size',    #for traffic test
            'dynamic_complete','dynamic_isl_loss','dynamic_ground_link_loss','dynamic_ground_link_rtt','dynamic_uplink_bw','dynamic_downlink_bw','dynamic_ground_link_bw','dynamic_isl_bw','dynamic_bw_fluct',  #not good
            'test_type',    #owdTest,throughputTest,trafficTest,throughputWithTraffic
            'analyse_callback',  #lineChart,cdf
            'sendq_length',
            'src','dst',
            'route_algorithm'   #relay_only , with_isl
            #'isRttTest','isFlowTest'
    ]

# n is satllite number
def gen_linear_topo(n,has_dummy_node=False):
    name = "%d_mid"%(n)
    numMidNode = n
    if has_dummy_node:
        nodes = ['h1','gs1']+['m%d'%(i+1) for i in range(n)]+['gs2','dummy','h2']
    else:
        nodes = ['h1','gs1']+['m%d'%(i+1) for i in range(n)]+['gs2','h2']
    links = [[nodes[i],nodes[i+1]] for i in range(len(nodes)-1)]
    return TopoParam(name=name,numMidNode=numMidNode,nodes=nodes,links=links)
	
# don't change these
#
Topo1 = TopoParam(name='1_mid',numMidNode=1,nodes=['h1','pep1','h2'],links=[['h1','pep1'],['pep1','h2']])
Topo2 = TopoParam(name='2_mid',numMidNode=2,nodes=['h1','pep1','pep2','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','h2']])
Topo3 = TopoParam(name='3_mid',numMidNode=3,nodes=['h1','pep1','pep2','pep3','h2'],links=[['h1','pep1'],['pep1','pep2'],['pep2','pep3'],['pep3','h2']])

#dynamic_test_topo = gen_test_trace()
dynamic_extreme_topo = gen_extreme_trace()   #for test
#dynamic_real_topo = get_trace(6,9,0,600)
dynamic_topo_exp2 = gen_link_change_trace()
#beijing_paris = get_trace(6,24,0,600)
# 
DefaultLP = LinkParam(
        loss=0, rtt=100, bw=20,
        itmTotal=20, itmDown=0,
        varBw=0, varIntv=5,varMethod='square')
# 
DefaultAP = MyAppParam(
        # max_queue_size=1000,txqueuelen=1000,
        sendTime=180,sendRound=1,
        e2eCC='cubic', midCC='nopep',protocol='INTCP',
        dynamic=0,dynamic_intv=1,
        data_size=0,
        dynamic_complete=True,dynamic_isl_loss=0.1,dynamic_ground_link_loss=0,dynamic_ground_link_rtt=50,dynamic_uplink_bw=5,dynamic_downlink_bw=20,dynamic_ground_link_bw=20,dynamic_isl_bw=20,dynamic_bw_fluct=False,
        analyse_callback="lineChart",test_type="throughputTest",
        sendq_length = 10000,
        src=-1,dst=-1,
        route_algorithm = "with_isl"
        #isRttTest=0,isFlowTest=0
        )


def getTestParamSet(tpsetName):
    tpSet = None
    if tpsetName == "static_test":    #retran test
        tpSet = TestParamSet(tpsetName,
                gen_linear_topo(2),
                LinksParam(DefaultLP.set(bw=5,loss=0,rtt=50), 
                    {'gs1_m1':{'rtt':50},
                    'm2_gs2':{'rtt':50}}),
                DefaultAP.set(sendTime=60),
                keyX = 'defaultLP.loss',
                keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
                {'defaultLP.loss':[0]#0,4,8,12,16
                },
                {
                'in_pep':{'midCC':'pep','protocol':'INTCP'},
                #'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
                
                }
        )

    if tpsetName == "dynamic_test":
        tpSet = TestParamSet(tpsetName,
            beijing_paris,None,
            DefaultAP.set(dynamic=1,dynamic_complete=False,sendTime=600),
            keyX = 'dynamic_isl_loss',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                'dynamic_isl_loss':[0,1]#0.01,0.1,1
            },
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             #'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
             #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'},
             #'westwood':{'midCC':'nopep','e2eCC':'westwood','protocol':'TCP'},
             #'westwood_pep':{'midCC':'westwood','e2eCC':'westwood','protocol':'TCP'},
             #'hybla':{'midCC':'nopep','e2eCC':'hybla','protocol':'TCP'},
             #'hybla_pep':{'midCC':'hybla','e2eCC':'hybla','protocol':'TCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             #'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })
    
    if tpsetName == "dynamic_complex_test": # isl loss=0.1, no downlink bandwidth fluctuation
        tpSet = TestParamSet(tpsetName,
            dynamic_real_topo,None,
            DefaultAP.set(dynamic=1,dynamic_complete=False,sendTime=600,dynamic_intv=1),
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add({},
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
             'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'},
             'westwood':{'midCC':'nopep','e2eCC':'westwood','protocol':'TCP'},
             'westwood_pep':{'midCC':'westwood','e2eCC':'westwood','protocol':'TCP'},
             'hybla':{'midCC':'nopep','e2eCC':'hybla','protocol':'TCP'},
             'hybla_pep':{'midCC':'hybla','e2eCC':'hybla','protocol':'TCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })
    if tpsetName == "dynamic_sim_test_1": # isl loss=0.1, no downlink bandwidth fluctuation
        tpSet = TestParamSet(tpsetName,
            dynamic_real_topo,None,
            DefaultAP.set(dynamic=1,dynamic_complete=False,sendTime=600),
            keyX = 'dynamic_isl_loss',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                'dynamic_isl_loss':[0.01,0.1,0.2,0.4,0.6,0.8,1]#0.01,0.1,0.2,0.4,0.6,0.8,1
            },
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             #'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
             #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'},
             #'westwood':{'midCC':'nopep','e2eCC':'westwood','protocol':'TCP'},
             #'westwood_pep':{'midCC':'westwood','e2eCC':'westwood','protocol':'TCP'},
             #'hybla':{'midCC':'nopep','e2eCC':'hybla','protocol':'TCP'},
             #'hybla_pep':{'midCC':'hybla','e2eCC':'hybla','protocol':'TCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })
    if tpsetName == "dynamic_sim_test_2": # isl loss=0.1, with downlink bandwidth fluctuation
        tpSet = TestParamSet(tpsetName,
            dynamic_real_topo,None,
            DefaultAP.set(dynamic=1,dynamic_complete=False,dynamic_bw_fluct=True,sendTime=600,analyse_callback="cdf"),
            keyX = 'dynamic_isl_loss',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                'dynamic_isl_loss':[1]   #0.01,0.1,0.2,0.4,0.6,0.8,1
            },
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             #'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
             #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'},
             #'westwood':{'midCC':'nopep','e2eCC':'westwood','protocol':'TCP'},
             #'westwood_pep':{'midCC':'westwood','e2eCC':'westwood','protocol':'TCP'},
             #'hybla':{'midCC':'nopep','e2eCC':'hybla','protocol':'TCP'},
             #'hybla_pep':{'midCC':'hybla','e2eCC':'hybla','protocol':'TCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })
    if tpsetName == "dynamic_sim_test_3":   #sendq =50
        tpSet = TestParamSet(tpsetName,
            dynamic_real_topo,None,
            DefaultAP.set(dynamic=1,dynamic_complete=False,dynamic_bw_fluct=True,sendTime=600,test_type="throughputWithOwd",analyse_callback="bar"),
            keyX = 'dynamic_isl_loss',
            keysCurveDiff=['protocol','midCC','e2eCC','dynamic_isl_loss'])
        tpSet.add(
            {
                'dynamic_isl_loss':[1]#0.2,0.5,1
            },
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             #'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })
    if tpsetName == "dynamic_sim_test_3_backup":   #sendq =1000
        tpSet = TestParamSet(tpsetName,
            dynamic_real_topo,None,
            DefaultAP.set(dynamic=1,dynamic_complete=False,dynamic_bw_fluct=True,sendTime=600,test_type="throughputWithOwd",analyse_callback="cdf"),
            keyX = 'dynamic_isl_loss',
            keysCurveDiff=['protocol','midCC','e2eCC','dynamic_isl_loss'])
        tpSet.add(
            {
                'dynamic_isl_loss':[1]#0.2,0.5,1
            },
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             #'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })

    if tpsetName == "distance_test_with_isl":   #sendq=50 , queue=5000, rtt0=30
        tpSet = TestParamSet(tpsetName,
            None,None,
            DefaultAP.set(dynamic=1,dynamic_complete=False,dynamic_bw_fluct=True,sendTime=600,test_type="throughputWithOwd",analyse_callback="bar"),
            keyX = 'dst',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                'dynamic_isl_loss':[1]#0.2,0.5,1
            },
            {
             #'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
             'in_pep':{'midCC':'pep','protocol':'INTCP'}
            },
            {
                'beijing_hangkong':{'src':6,'dst':45},
                #'beijing_singapore':{'src':6,'dst':63},
                #'beijing_kabul':{'src':6,'dst':80},
                #'beijing_peterberg':{'src':6,'dst':73},
                'beijing_paris':{'src':6,'dst':24},
                'beijing_newyork':{'src':6,'dst':9},
                #'beijing_medellin':{'src':6,'dst':97},
            })
    if tpsetName == "distance_test_with_isl_backup":   #sendq =50
        tpSet = TestParamSet(tpsetName,
            None,None,
            DefaultAP.set(dynamic=1,dynamic_complete=False,dynamic_bw_fluct=True,sendTime=600,test_type="throughputWithOwd"),
            keyX = 'dynamic_isl_loss',
            keysCurveDiff=['protocol','midCC','e2eCC','dynamic_isl_loss'])
        tpSet.add(
            {
                'dynamic_isl_loss':[1]#0.2,0.5,1
            },
            {#'in_pep':{'midCC':'pep','protocol':'INTCP'},
             #'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             #'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            },
            {
                #'beijing_hangkong':{'src':6,'dst':45},
                #'beijing_kabul':{'src':6,'dst':80},
                #'beijing_singapore':{'src':6,'dst':63},
                #'beijing_peterberg':{'src':6,'dst':73},
                'beijing_paris':{'src':6,'dst':24},
                #'beijing_newyork':{'src':6,'dst':9},
                #'beijing_medellin':{'src':6,'dst':97},
            })   
    if tpsetName == "relay_only_test": # isl loss=0.1, with downlink bandwidth fluctuation
        origin_trace = get_trace(6,25,0,600,route_algorithm="relay_only")
        #dynamic_topo = get_complete_relay_only_trace(origin_trace,bw_fluctuation=True) 
        #print(dynamic_topo)
        tpSet = TestParamSet(tpsetName,
            origin_trace,None,
            DefaultAP.set(dynamic=1,dynamic_complete=False,dynamic_bw_fluct=True,sendTime=600,analyse_callback="cdf"),
            keyX = 'dynamic_isl_loss',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                'dynamic_isl_loss':[1]   #0.01,0.1,0.5,1
            },
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             #'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })

    if tpsetName == "relay_only_cdf_1":   #sendq =1000
        origin_trace = get_trace(6,25,0,600,route_algorithm="relay_only")
        dynamic_topo = get_complete_relay_only_trace(origin_trace,bw_fluctuation=True,uplink_loss=1,downlink_loss=1) 
        tpSet = TestParamSet(tpsetName,
            dynamic_topo,None,
            DefaultAP.set(dynamic=1,dynamic_complete=True,sendTime=600,test_type="throughputWithOwd",analyse_callback="cdf"),
            keyX = 'dynamic_isl_loss',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                #'dynamic_isl_loss':[0.2,0.5,1]#0.2,0.5,1
            },
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             #'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })
    if tpsetName == "beijing_shanghai_cdf":   #sendq =1000
        origin_trace = get_trace(6,2,0,600,route_algorithm="relay_only")
        dynamic_topo = get_complete_relay_only_trace(origin_trace,bw_fluctuation=True,uplink_loss=1,downlink_loss=1) 
        tpSet = TestParamSet(tpsetName,
            dynamic_topo,None,
            DefaultAP.set(dynamic=1,dynamic_complete=True,sendTime=600,test_type="throughputWithOwd",analyse_callback="cdf"),
            keyX = 'dynamic_isl_loss',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                #'dynamic_isl_loss':[0.2,0.5,1]#0.2,0.5,1
            },
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             #'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })
    if tpsetName == "dynamic_exp_2": #relative normal environment, need reduce loss?
        tpSet = TestParamSet(tpsetName,
            dynamic_topo_exp2,None,
            DefaultAP.set(dynamic=1,sendTime=120),
            keyX = 'dynamic_intv',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                'dynamic_intv':[5,10,15,20] #1,
            },
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
             'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'},
             'westwood':{'midCC':'nopep','e2eCC':'westwood','protocol':'TCP'},
             'westwood_pep':{'midCC':'westwood','e2eCC':'westwood','protocol':'TCP'},
             'hybla':{'midCC':'nopep','e2eCC':'hybla','protocol':'TCP'},
             'hybla_pep':{'midCC':'hybla','e2eCC':'hybla','protocol':'TCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })
    # for final use
    if tpsetName == "dynamic_exp_4": # normal dynamic topo with different loss
        tpSet = TestParamSet(tpsetName,
            dynamic_topo_exp2,None,
            DefaultAP.set(dynamic=1,dynamic_complete=False,dynamic_ground_link_rtt=20,dynamic_uplink_bw=20,sendTime=120),
            keyX = 'dynamic_intv',
            keysCurveDiff=['protocol','midCC','e2eCC','dynamic_isl_loss'])
        tpSet.add(
            {   
                'dynamic_isl_loss':[0.05],#0.01,0.02,0.05,0.1
                'dynamic_intv':[1,2,5,10,15,20] #1,2,5,10,15,20
            },
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             #'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             #'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
             #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'},
             'westwood':{'midCC':'nopep','e2eCC':'westwood','protocol':'TCP'},
             #'westwood_pep':{'midCC':'westwood','e2eCC':'westwood','protocol':'TCP'},
             #'hybla':{'midCC':'nopep','e2eCC':'hybla','protocol':'TCP'},
             #'hybla_pep':{'midCC':'hybla','e2eCC':'hybla','protocol':'TCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })
    if tpsetName == "dynamic_exp_3": #extreme environment
        tpSet = TestParamSet(tpsetName,
            dynamic_extreme_topo,None,
            DefaultAP.set(dynamic=1,sendTime=120),
            keyX = 'dynamic_intv',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                'dynamic_intv':[1,2,5,10] #1,2,5,10
            },
            {'in_pep':{'midCC':'pep','protocol':'INTCP'},
             #'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
             #'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
             #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'},
             #'westwood':{'midCC':'nopep','e2eCC':'westwood','protocol':'TCP'},
             #'westwood_pep':{'midCC':'westwood','e2eCC':'westwood','protocol':'TCP'},
             #'hybla':{'midCC':'nopep','e2eCC':'hybla','protocol':'TCP'},
             #'hybla_pep':{'midCC':'hybla','e2eCC':'hybla','protocol':'TCP'},
             'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
             'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            })
    if tpsetName == "pure":
        tpSet = TestParamSet(tpsetName,
            Topo1,
            LinksParam(DefaultLP.set(bw=40,rtt=100), 
            {'pep1_h2':{'bw':40,'itmDown':0,'itmTotal':20},
            }
            ),
            DefaultAP)
        tpSet.add({})

    if tpsetName == "bp_itm_test_1":
        tpSet = TestParamSet(tpsetName,
            Topo1,
            LinksParam(DefaultLP.set(rtt=6,bw=20,loss=0), 
            {'h1_pep1':{'bw':40,'itmTotal':40},
            }),
            DefaultAP.set(sendTime=120),
            keyX = 'h1_pep1.itmDown',
            keysCurveDiff=['protocol'])
        tpSet.add(
            {'h1_pep1.itmDown':[3,0]#1,2,3,4]
            },
            {
            'in_pep':{'midCC':'pep','protocol':'INTCP'},
            # 'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
            #'hybla':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'}
            }
        )
    if tpsetName == "bp_varbw_test_1":
        tpSet = TestParamSet(tpsetName,
                Topo1,
                LinksParam(DefaultLP.set(bw=20,loss=0), 
                    {'h1_pep1':{'rtt':6,'varBw':16},
                    'pep1_h2':{'rtt':6}}),
                DefaultAP.set(sendTime=30),
                keyX = 'h1_pep1.varIntv',
                keysCurveDiff=['protocol'])
        tpSet.add(
                {'h1_pep1.varIntv':[8]#[2]#,4,6,8]
                },
                {
                # 'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
                'in_pep':{'midCC':'pep','protocol':'INTCP'},
                # 'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'}
                # 'hybla':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
                
                }
        )
    if tpsetName == "bp_varbw_test_2":
        tpSet = TestParamSet(tpsetName,
                Topo1,
                LinksParam(DefaultLP.set(bw=20,loss=0), 
                    {'h1_pep1':{'rtt':50,'varIntv':8},
                    'pep1_h2':{'rtt':100}}),
                DefaultAP.set(sendTime=30),
                keyX = 'h1_pep1.varBw',
                keysCurveDiff=['protocol'])
        tpSet.add(
                {'h1_pep1.varBw':[0,4,8,12,16]
                },
                {
                'in_pep':{'midCC':'pep','protocol':'INTCP'},
                'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'}
                #'hybla':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
                
                }
        )
    if tpsetName == "expr":
        tpSet = TestParamSet(tpsetName,
                Topo3,
                LinksParam(DefaultLP.set(rtt=5,bw=50,loss=0.1),
                    {'h1_pep1':{'rtt':100,'loss':0},
                    'pep1_pep2':{'bw':20}}),
                DefaultAP.set(sendTime=30),
                keyX='defaultLP.loss',
                keysCurveDiff=['protocol'])
        tpSet.add(
                {'defaultLP.loss':[0,0.1,0.01]#0.1,0.5,1],
                },
                {
                # 'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
                'in_pep':{'midCC':'pep','protocol':'INTCP'}
                }
        )
    if tpsetName == "expr0":
        tpSet = TestParamSet(tpsetName,
                Topo1,
                LinksParam(DefaultLP.set(loss=0), 
                    {'h1_pep1':{'bw':20,'rtt':6,'varBw':5},
                    'pep1_h2':{'bw':20,'rtt':6}}),
                DefaultAP.set(sendTime=60),
                keyX = 'h1_pep1.varIntv',
                keysCurveDiff=['protocol'])
        tpSet.add(
                {'h1_pep1.varIntv':[10]#[2,4,6,8]
                },
                {
                # 'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
                'in_pep':{'midCC':'pep','protocol':'INTCP'}
                }
        )
    if tpsetName == "expr3":
        tpSet = TestParamSet(tpsetName,
                Topo3,
                LinksParam(DefaultLP.set(varIntv=20,loss=0.1), 
                    {'h1_pep1':{'bw':40},
                    'pep3_h2':{'bw':40},
                    'pep2_pep3':{'bw':40,'varBw':15}}),
                DefaultAP.set(sendTime=360),
                keyX='pep2_pep3.varIntv',
                keysCurveDiff=['midCC'])
        tpSet.add(
                {'pep2_pep3.varIntv':[2,4,6,8],
                },
                {
                # 'bbr':{'e2eCC':'bbr','protocol':'TCP'},
                'in_nopep':{'midCC':'nopep'},
                'in_pep':{'midCC':'pep'}
                }
        )
    if tpsetName == "retran_test":    #retran test
        tpSet = TestParamSet(tpsetName,
            gen_linear_topo(2),
            LinksParam(DefaultLP.set(rtt=20,bw=40,loss=1), 
            {#'h1_gs1':{'rtt':100,'loss':1},
            #'gs2_h2':{'rtt':100,'loss':1},
            }),
            DefaultAP.set(sendTime=300,test_type="owdTest"),
            keyX = 'h1_pep1.itmDown',
            keysCurveDiff=['protocol','midCC','e2eCC','defaultLP.loss'])
        tpSet.add(
            {
                'defaultLP.loss':[0.2,1,2]#0.1,0.2,0.5,1,2
            },
            {
            'in_pep':{'midCC':'pep','protocol':'INTCP'},
            #'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
            'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
            #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'}
            }
        )
    if tpsetName == "retran_test_2":    #retran test
        tpSet = TestParamSet(tpsetName,
            gen_linear_topo(2),
            LinksParam(DefaultLP.set(rtt=20,bw=40,loss=1), 
            {'h1_gs1':{'loss':0},
            'gs2_h2':{'loss':0},
            }),
            DefaultAP.set(sendTime=300,test_type="owdTest"),
            keyX = 'h1_pep1.itmDown',
            keysCurveDiff=['protocol','midCC','defaultLP.loss'])
        tpSet.add(
            {
                'defaultLP.loss':[0.1,0.2,0.5,1]   #0.1,0.5,1],
            },
            {
            'in_pep':{'midCC':'pep','protocol':'INTCP'},
            'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
            'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'}
            }
        )
    if tpsetName == "big_rtt_retran_test":    #retran test
        tpSet = TestParamSet(tpsetName,
            gen_linear_topo(0),
            LinksParam(DefaultLP.set(rtt=50,bw=40,loss=1), 
            {#'h1_gs1':{'rtt':100,'loss':1},
            #'gs2_h2':{'rtt':100,'loss':1},
            }),
            DefaultAP.set(sendTime=300,test_type="owdTest"),
            keyX = 'h1_pep1.itmDown',
            keysCurveDiff=['protocol','midCC','defaultLP.loss'])
        tpSet.add(
            {
                'defaultLP.loss':[0.1,0.2,0.5,1]#0.1,0.5,1],
            },
            {
            'in_pep':{'midCC':'pep','protocol':'INTCP'},
            'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
            #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'}
            }
        )
    if tpsetName == "big_rtt_retran_test_2":    #retran test
        tpSet = TestParamSet(tpsetName,
            gen_linear_topo(0),
            LinksParam(DefaultLP.set(rtt=50,bw=40,loss=1), 
            {#'h1_gs1':{'rtt':100,'loss':1},
            #'gs2_h2':{'rtt':100,'loss':1},
            }),
            DefaultAP.set(sendTime=300,test_type="owdTest"),
            keyX = 'h1_pep1.itmDown',
            keysCurveDiff=['protocol','midCC','defaultLP.loss'])
        tpSet.add(
            {
                'defaultLP.loss':[0,1,0.5,0.1,0.2]#0.1,0.5,1],
            },
            {
            'in_pep':{'midCC':'pep','protocol':'INTCP'},
            'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
            'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'}
            }
        )
    if tpsetName == "final_varbw_test_1":
        tpSet = TestParamSet(tpsetName,
                gen_linear_topo(2),
                LinksParam(DefaultLP.set(bw=20,loss=0,rtt=20), 
                    {'gs1_m1':{'rtt':10,'varIntv':8},
                    'm2_gs2':{'rtt':10}}),
                DefaultAP.set(sendTime=120),
                keyX = 'gs1_m1.varBw',
                keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
                {'gs1_m1.varBw':[0,4,8,12,16]#0,4,8,12,16
                },
                {
                'in_pep':{'midCC':'pep','protocol':'INTCP'},
                #'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
                #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'}
                'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
                'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'}
                }
        )
    if tpsetName == "owd_thrp_balance_varbw_test":
        tpSet = TestParamSet(tpsetName,
                gen_linear_topo(2),
                LinksParam(DefaultLP.set(bw=20,loss=0,rtt=20), 
                    {'gs1_m1':{'rtt':10,'varIntv':8,'varBw':12},
                    'm2_gs2':{'rtt':10}}),
                DefaultAP.set(sendTime=120,test_type="owdThroughputBalance"),
                keyX = 'gs1_m1.varBw',
                keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
                {'sendq_length':[0,20,200,500,1000,2000,4000,6000,8000]#0,20,200,500,1000,2000,4000,6000,8000
                },
                {
                'in_pep':{'midCC':'pep','protocol':'INTCP'},
                'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
                #'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
                'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'}
                }
        )
    if tpsetName == "owd_thrp_balance_itm_test":
        tpSet = TestParamSet(tpsetName,
                gen_linear_topo(2),
                LinksParam(DefaultLP.set(bw=20,loss=0,rtt=20), 
                    {'gs1_m1':{'rtt':10,'bw':40,'itmTotal':20,'itmDown':2},
                    'm2_gs2':{'rtt':10}}),
                DefaultAP.set(sendTime=120,test_type="owdThroughputBalance"),
                keyX = 'gs1_m1.varBw',
                keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
                {'sendq_length':[0,20,400,600,750,1000,2000,4000,10000]#0,20,50,200,500,600,750,1000,2000,4000,10000/0,20,500,1000,2000,4000
                },
                {
                'in_pep':{'midCC':'pep','protocol':'INTCP'},
                'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
                'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'}
                }
        )
    if tpsetName == "final_itm_test_1":
        tpSet = TestParamSet(tpsetName,
                gen_linear_topo(2),
                LinksParam(DefaultLP.set(bw=20,loss=0,rtt=20), 
                    {'gs1_m1':{'rtt':10,'bw':40,'itmTotal':20},
                    'm2_gs2':{'rtt':10}}),
                DefaultAP.set(sendTime=120),
                keyX = 'gs1_m1.itmDown',
                keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
                {'gs1_m1.itmDown':[0,1,2,3,4]   #0,1,2,3,4
                },
                {
                'in_pep':{'midCC':'pep','protocol':'INTCP'},
                'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
                'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
                #'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
                #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'}
                #'hybla':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
                
                }
        )
    # for final test
    if tpsetName == "loss_test_1":
        tpSet = TestParamSet(tpsetName,
                gen_linear_topo(5),
                LinksParam(DefaultLP.set(bw=20,loss=0,rtt=20), 
                    {'gs1_m1':{'rtt':10},
                    'm2_gs2':{'rtt':10},
                    'h1_gs1':{'loss':0},
                    'gs2_h2':{'loss':0}}),
                DefaultAP.set(sendTime=120),
                keyX = 'defaultLP.loss',
                keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
                {'defaultLP.loss':[0,0.01,0.1,0.2,0.4,0.6,0.8,1]   #0,0.1,0.5,1
                },
                {
                'in_pep':{'midCC':'pep','protocol':'INTCP'},
                #'in_nopep':{'midCC':'nopep','protocol':'INTCP'},
                'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
                #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'},
                #'westwood':{'midCC':'nopep','e2eCC':'westwood','protocol':'TCP'},
                #'westwood_pep':{'midCC':'westwood','e2eCC':'westwood','protocol':'TCP'},
                'hybla':{'midCC':'nopep','e2eCC':'hybla','protocol':'TCP'},
                #'hybla_pep':{'midCC':'hybla','e2eCC':'hybla','protocol':'TCP'},
                'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
                'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
                
                }
        )
    if tpsetName == "flow_test":    #for 20MB
        tpSet = TestParamSet(tpsetName,
            gen_linear_topo(2,has_dummy_node=True),
            LinksParam(DefaultLP.set(rtt=20,bw=20), 
            {'gs2_dummy':{'rtt':10},
            'dummy_h2':{'loss':0,'rtt':10}
            }),
            DefaultAP.set(sendTime=60,test_type="trafficTest",data_size=20),
            keyX = 'defaultLP.loss',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                'defaultLP.loss':[0,1,2]#0,0.2,0.4,0.6,0.8,1,1.2,1.4,1.6,1.8,2
            },
            {
            #'in_pep':{'midCC':'pep','protocol':'INTCP'},
            'cubic':{'midCC':'nopep','e2eCC':'cubic','protocol':'TCP'},
            #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'}
            }
        )
    if tpsetName == "flow_test_2":    #for 100MB
        tpSet = TestParamSet(tpsetName,
            gen_linear_topo(2,has_dummy_node=True),
            LinksParam(DefaultLP.set(rtt=20,bw=20), 
            {'gs2_dummy':{'rtt':10},
            'dummy_h2':{'loss':0,'rtt':10}
            }),
            DefaultAP.set(sendTime=120,test_type="trafficTest",data_size=100),
            keyX = 'defaultLP.loss',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                'defaultLP.loss':[0,0.2,0.4,0.6,0.8,1,1.2,1.4,1.6,1.8,2]#0,0.2,0.4,0.6,0.8,1,1.2,1.4,1.6,1.8,2
            },
            {
            'in_pep':{'midCC':'pep','protocol':'INTCP'},
            'cubic':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
            #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'}
            }
        )
    if tpsetName == "throughput_with_traffic":    #for 100MB
        tpSet = TestParamSet(tpsetName,
            gen_linear_topo(2,has_dummy_node=True),
            LinksParam(DefaultLP.set(rtt=20,bw=20), 
            {'gs2_dummy':{'rtt':10},
            'dummy_h2':{'loss':0,'rtt':10}
            }),
            DefaultAP.set(sendTime=60,test_type="throughputWithTraffic"),
            keyX = 'defaultLP.loss',
            keysCurveDiff=['protocol','midCC','e2eCC'])
        tpSet.add(
            {
                'defaultLP.loss':[0,0.5,1,1.5,2]#0,0.5,1,1.5,2,2.5,3
            },
            {
            'in_pep':{'midCC':'pep','protocol':'INTCP'},
            'bbr':{'midCC':'nopep','e2eCC':'bbr','protocol':'TCP'},
            #'pcc':{'midCC':'nopep','e2eCC':'pcc','protocol':'TCP'},
            #'cubic_pep':{'midCC':'cubic','e2eCC':'cubic','protocol':'TCP'}
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
