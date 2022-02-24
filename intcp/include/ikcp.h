//=====================================================================
// 
// Based on:
// KCP - A Better ARQ Protocol Implementation
// skywind3000 (at) gmail.com, 2010-2011
//  
//=====================================================================

#ifndef __INTCP_H__
#define __INTCP_H__

#include <assert.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <cstring>
#include <cmath>

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include <list>
#include <memory> // for shared_ptr

#include "generality.h"
#include "log.h"

using namespace std;

#define INTCP_ROLE_REQUESTER 10
#define INTCP_ROLE_RESPONDER 11
#define INTCP_ROLE_MIDNODE 12

#define INTCP_RTT_SCHM_MAXWND 1
#define INTCP_RTT_SCHM_EXPO 2

#define INTCP_CC_SCHM_LOSSB 1
#define INTCP_CC_SCHM_RTTB 2

#define INTCP_CC_SLOW_START 0
#define INTCP_CC_CONG_AVOID 1


const IUINT32 INTCP_OVERHEAD = 23;            //intcp, header include rangestart & rangeend
const IUINT32 INTCP_MTU = 1400;
const IUINT32 INTCP_MSS = INTCP_MTU - INTCP_OVERHEAD;
const IUINT32 INTCP_INT_RANGE_LIMIT = 20*INTCP_MSS;

const IUINT32 INTCP_UPDATE_INTERVAL = 5; //Unit: ms
const IUINT32 INTCP_DEADLINK = 8;

const IUINT32 INTCP_CMD_INT = 80;         // cmd: interest 
const IUINT32 INTCP_CMD_PUSH = 81;        // cmd: push data


// Retransmission
const int RTTscheme = INTCP_RTT_SCHM_EXPO;
const IUINT32 INTCP_RTO_MIN = 20;        // normal min rto
const IUINT32 INTCP_RTO_DEF = 10000;      //500
const IUINT32 INTCP_RTO_MAX = 60000;
const float INTCP_RTO_EXPO = 1.1;//TODO simplify timeout mechanism

const IUINT32 INTCP_SNHOLE_TIMEOUT = 1000; // after 1000ms, don't care anymore
const IUINT32 INTCP_SNHOLE_THRESHOLD = 5; // if three segs 

// Congestion control
const int CCscheme = INTCP_CC_SCHM_RTTB;

const IUINT32 INTCP_SSTHRESH_INIT = 100; // 300 -> 600 -> 100
const IUINT32 INTCP_CWND_MIN = 2;       //2 MSS//TODO calculated by SENDRATE_MIN
const IUINT32 INTCP_RTT0 = 10; // like hybla

// RTT-based
const float QueueingThreshold = 10000; // unit: byte //20000
const IUINT32 HrttMinWnd = 10000; // unit: ms

const IUINT32 INTCP_SNDQ_MAX = 10000*INTCP_MSS; //NOTE
const IUINT32 INTCP_INTB_MAX = 20000*INTCP_MSS;
const IUINT32 INTCP_WND_RCV = 128; // for app recv buffer

const float INTCP_SENDRATE_MIN = 0.1; //Mbps
const float INTCP_SENDRATE_MAX = 300;


//=====================================================================
// SEGMENT
//=====================================================================
struct IntcpSeg
{
    IUINT32 cmd;    //need send,1B
    IINT16 wnd;    //need send,2B
    IUINT32 ts;        //need send,4B
    IUINT32 sn;        //need send,4B
    IUINT32 len;    //need send,4B
    //intcp
    IUINT32 rangeStart;    //need send,4B 
    IUINT32 rangeEnd;    //TODO don't need send,4B 
    
    // IUINT32 firstTs; //first time this interest is sent. ts >= firstTs
    // bool rttUpdate; // is this interest allowed to be used in rtt update
    IUINT32 xmit; // send time count
    
    char data[1];    //need send
};

struct ByteRange
{
    //TODO remove ts?
    // ts is for rtt caclulation: 
    // when response interest in pendingInts, 
    // copy the ts of interest to data packet header
    IUINT32 startByte, endByte, ts;
};

struct Hole
{
    IUINT32 startSn, endSn; //packet level(sn)
    IUINT32 startByte, endByte; //byte level
    IUINT32 ts;
    int count;
};

class StatInfo
{
public:
    int ssid;
    IUINT32 startTs;

    int xmit;
    IUINT32 lastPrintTs;
    int recvedUDP; // Mbps
    int recvedINTCP;
    int sentINTCP;
    int cntTimeout,cntIntHole,cntDataHole;

    void reset(){
        int ssidTmp=ssid;
        IUINT32 startTsTmp=startTs;
        memset(this,0,sizeof(*this));
        ssid = ssidTmp;
        startTs = startTsTmp;
        lastPrintTs = _getMillisec();
    }
    void init(){
        IUINT32 current = _getMillisec();
        ssid = current%10000;
        startTs = current;
        reset();
    }
};

struct RcvBufItr
{
    //TODO remove ts?
    // ts is for rtt caclulation: 
    // when response interest in pendingInts, 
    // copy the ts of interest to data packet header
    IUINT32 startByte, endByte;
    list<shared_ptr<IntcpSeg>>::iterator itr;
};
//---------------------------------------------------------------------
// IntcpTransCB
//---------------------------------------------------------------------
class IntcpTransCB
{
private:
	int state;
	IUINT32 updated, nextFlushTs, lastFlushTs;
    StatInfo stat;


   	int nodeRole;

    //requester
    list<ByteRange> intQueue;
    list<shared_ptr<IntcpSeg>> intBuf;
    list<shared_ptr<IntcpSeg>> rcvBuf;
    list<RcvBufItr> rcvBufItrs;

	IUINT32 rcvNxt; // for ordered data receiving
    list<shared_ptr<IntcpSeg>> rcvQueue;
    //responder
    list<ByteRange> pendingInts;
    list<shared_ptr<IntcpSeg>> sndQueue;
    shared_ptr<char> tmpBuffer;

    /* ------------ Loss Recovery --------------- */
    // end-to-end timeout
    int srtt, rttvar, rto;
    // maxRtt window
    list<int> rttQueue;
    // exponential
    int conseqTimeout;

    // hop-by-hop sn hole
	IUINT32 dataNextSn, intNextSn;
    IUINT32 dataSnRightBound, dataByteRightBound, dataRightBoundTs;
    IUINT32 intSnRightBound, intByteRightBound, intRightBoundTs;
    list<Hole> dataHoles, intHoles;
    
    
    /* ----- hop-by-hop Congestion Control ----- */
    // Flow control
    int rmt_sndq_rest;
    int intOutputLimit;

    int ccState;
    int ccDataLen;
    IUINT32 cwnd;
    
    int intHopOwd, hopSrtt, hopRttvar;
    // if there is no interest to send in short-term future, 
    // requester needs to send empty interest for sendRate notification
    // this is particularly necessary in slow start phase
    IUINT32 lastSendIntTs;
    // throughput calculation for rtt-based CC and app-limited detection
    IUINT32 lastThrpUpdateTs;
    int recvedBytesLastHRTT, recvedBytesThisHRTT;
    float thrpLastHRTT; // Mbps

    // congestion signal
    // loss-based
    bool hasLossEvent;
    // RTT-based
    list<pair<IUINT32,int>> hrttQueue;

    // to avoid severe cwnd decreasing in one hrtt
    IUINT32 lastCwndDecrTs;

    // send rate limitation for queue length control
    int sndQueueBytes, intBufBytes;
    // int rmt_sndq_rest;

    // send rate notification and implementation
    float rmtSendRate; // Mbps
    int dataOutputLimit;



    
    void *user;
    int (*outputFunc)(const char *buf, int len, void *user, int dstRole);
	// set callback called by responseInterest
	int (*fetchDataFunc)(char *buf, IUINT32 start, IUINT32 end, void *user);
    int (*onUnsatInt)(IUINT32 start, IUINT32 end, void *user);
	// also called by responseInterest


    // allocate a new kcp segment
    shared_ptr<IntcpSeg> createSeg(int size);
    char* encodeSeg(char *ptr, const IntcpSeg *seg);

    // flush pending data
    void flush();
    void flushIntQueue();
    void flushIntBuf();
    void flushData();
    
    int output(const void *data, int size, int dstRole);
    int outputInt(IUINT32 rangeStart, IUINT32 rangeEnd);
    void updateRTT(IINT32 rtt, int xmit);
    void updateHopRTT(IINT32 hop_rtt);

    void detectIntHole(IUINT32 rangeStart, IUINT32 rangeEnd, IUINT32 sn);
    bool detectDataHole(IUINT32 rangeStart, IUINT32 rangeEnd, IUINT32 sn);
    // after input
    void parseInt(IUINT32 rangeStart,IUINT32 rangeEnd);

    // returns below zero for error
    int sendData(const char *buffer, IUINT32 start, IUINT32 end);

    void parseData(shared_ptr<IntcpSeg> newseg);
    
    void moveToRcvQueue();
    
    IINT16 getDataSendRate();
    IINT16 getIntDev();
    
    void updateCwnd(IUINT32 dataLen);
    
    bool allow_cwnd_increase();
    bool allow_cwnd_decrease(IUINT32 current);
//---------------------------------------------------------------------
// API
//---------------------------------------------------------------------
public:
    // from the same connection. 'user' will be passed to the output callback
    IntcpTransCB(void *user, 
			int (*_outputFunc)(const char *buf, int len, void *user, int dstRole), 
			int (*_fetchDataFunc)(char *buf, IUINT32 start, IUINT32 end, void *user),
			int (*_onUnsatInt)(IUINT32 start, IUINT32 end, void *user),
			// bool _isUnreliable,
			int _nodeRole
	);
    IntcpTransCB(){}
    // release kcp control object
    // ~IntcpTransCB();

    // intcp user/upper level request
    int request(IUINT32 rangeStart,IUINT32 rangeEnd);

    // when you received a low level packet (eg. UDP packet), call it
    int input(char *data, int size);

    void notifyNewData(const char *buffer, IUINT32 start, IUINT32 end);

    // update state (call it repeatedly, every 10ms-100ms), or you can ask 
    // ikcp_check when to call it again (without ikcp_input/_send calling).
    // 'current' - current timestamp in millisec. 
    void update();

    // Determine when should you invoke ikcp_update:
    // returns when you should invoke ikcp_update in millisec, if there 
    // is no ikcp_input/_send calling. you can call ikcp_update in that
    // time, instead of call update repeatly.
    // Important to reduce unnacessary ikcp_update invoking. use it to 
    // schedule ikcp_update (eg. implementing an epoll-like mechanism, 
    // or optimize ikcp_update when handling massive kcp connections)
    IUINT32 check();

    // user/upper level recv: returns size, returns below zero for EAGAIN
    int recv(char *buffer, int maxBufSize, IUINT32 *startPtr, IUINT32 *endPtr);

    static int judgeSegDst(const char *p, long size);

//---------------------------------------------------------------------
// rarely use
//---------------------------------------------------------------------
    // get how many packet is waiting to be sent
    IUINT32 getCwnd();
    int getWaitSnd();
    int getRwnd();
    // check the size of next message in the recv queue
    int peekSize();
};


float bytesToMbit(int bytes);
int mbitToBytes(float mbit);

#endif
