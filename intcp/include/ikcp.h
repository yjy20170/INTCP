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

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#include <list>
#include <memory> // for shared_ptr

#include "generality.h"
#include "log.h"

using namespace std;

#define INTCP_REQUESTER 10
#define INTCP_RESPONSER 11
#define INTCP_MIDNODE 12

//=====================================================================
// KCP BASIC
//=====================================================================

const IUINT32 INTCP_OVERHEAD = 23;            //intcp, header include rangestart & rangeend

const IUINT32 INTCP_RTO_MIN = 20;        // normal min rto
const IUINT32 INTCP_RTO_DEF = 1000; //500
const IUINT32 INTCP_RTO_MAX = 60000;
const float INTCP_RTO_FACTOR = 1.05;

const IUINT32 INTCP_CMD_INT = 80;         // cmd: interest 
const IUINT32 INTCP_CMD_PUSH = 81;        // cmd: push data
const IUINT32 INTCP_CMD_WASK = 83;        // cmd: window probe (ask)
const IUINT32 INTCP_CMD_WINS = 84;        // cmd: window size (tell)

const IUINT32 INTCP_CMD_HOP_RTT_ASK = 85;
const IUINT32 INTCP_CMD_HOP_RTT_TELL = 86;

const IUINT32 INTCP_ASK_SEND = 1;        // need to send INTCP_CMD_WASK
const IUINT32 INTCP_ASK_TELL = 2;        // need to send INTCP_CMD_WINS
const IUINT32 INTCP_WND_SND = 32;
const IUINT32 INTCP_WND_RCV = 128;       // must >= max fragment size
const IUINT32 INTCP_MTU_DEF = 1400; //EXPR 1400
const IUINT32 INTCP_ACK_FAST = 3;
const IUINT32 INTCP_INTERVAL = 1; //EXPR 100 -> 5
const IUINT32 INTCP_DEADLINK = 8;
const IUINT32 INTCP_THRESH_INIT = 2;
const IUINT32 INTCP_THRESH_MIN = 2;
const IUINT32 INTCP_PROBE_INIT = 7000;        // 7 secs to probe window size
const IUINT32 INTCP_PROBE_LIMIT = 120000;    // up to 120 secs to probe window
const IUINT32 INTCP_FASTACK_LIMIT = 5;        // max times to trigger fastRetrans

const IUINT32 INTCP_SEQHOLE_TIMEOUT = 1000; // after 1000ms, don't care anymore
const IUINT32 INTCP_SEQHOLE_THRESHOLD = 3; // if three segs 

//=====================================================================
// SEGMENT
//=====================================================================
struct IntcpSeg
{
    IUINT32 cmd;    //need send,1B
    IUINT32 wnd;    //need send,2B
    IUINT32 ts;        //need send,4B
    IUINT32 sn;        //need send,4B
    IUINT32 len;    //need send,4B
    //intcp
    IUINT32 rangeStart;    //need send,4B 
    IUINT32 rangeEnd;    //need send,4B 
    
    IUINT32 firstTs;
    IUINT32 resendts;
    IUINT32 rto;
    IUINT32 xmit;
    
    
    char data[1];    //need send
};

struct IntRange
{
    // ts is for rtt caclulation: 
    // when response interest in recvedInts, 
    // copy the ts of interest to data packet header
    IUINT32 start, end, ts;
};

struct Hole
{
    IUINT32 start, end; //packet level(sn)
    IUINT32 byteStart, byteEnd; //byte level
    IUINT32 ts;
    int count;
};

//---------------------------------------------------------------------
// IntcpTransCB
//---------------------------------------------------------------------
class IntcpTransCB
{
private:
	int state, dead_link;

    IUINT32 mtu, mss;
    
	IUINT32 snd_nxt, rcv_nxt;    //still need rcv_nxt, snd_una & snd_nxt  may be discarded
	IUINT32 snd_nxt_int; // sn of interest, for interest seq hole detection
    int xmit;
    
    int nodelay, nocwnd; // about rto caclulation
    int rx_rttval, rx_srtt, rx_rto, rx_minrto;
    int hop_rttval, hop_srtt;
    int fastRetransThre, fastRetransCountLimit;
    IUINT32 snd_wnd, rcv_wnd, rmt_wnd, cwnd, ssthresh;
    
	IUINT32 updated, updateInterval, nextFlushTs;
    IUINT32 ts_probe, probe_wait, probe;
    IUINT32 ts_hop_rtt_probe,hop_rtt_probe_wait;
    
    //requester
    list<IntRange> int_queue;
    list<shared_ptr<IntcpSeg>> int_buf;
    list<shared_ptr<IntcpSeg>> rcv_buf;
    list<shared_ptr<IntcpSeg>> rcv_queue;
    //responser
    list<IntRange> recvedInts;
    list<shared_ptr<IntcpSeg>> snd_queue;

	// midnode solution 1 ---- one session has two unreliable TransCB
	// for requester
	// no timeout: interest in intlist will be directly output, thus no timeout detection.
	// still detects seq hole: when a seq hole is found, request it
	// for responser
	// no realignment: data will be directly push to rcv_queue
	// no PIT: unsatisfied interest will not be stored in recvedInts
	// bool isUnreliable;

	// midnode solution 2 ---- one TransCB
	int nodeRole;
    //seqhole
    IUINT32 dataSnRightBound, dataByteRightBound, dataRightBoundTs;
    IUINT32 intSnRightBound, intByteRightBound, intRightBoundTs;
    list<Hole> dataHoles, intHoles;
    void detectIntHole(IUINT32 rangeStart, IUINT32 rangeEnd, IUINT32 sn);
    void detectDataHole(IUINT32 rangeStart, IUINT32 rangeEnd, IUINT32 sn);
    
    void *user;
    int (*outputFunc)(const char *buf, int len, void *user, int dstRole);
	// set callback called by responseInterest
	int (*fetchDataFunc)(char *buf, IUINT32 start, IUINT32 end, void *user);
    int (*onUnsatInt)(IUINT32 start, IUINT32 end, void *user);
	// also called by responseInterest

    shared_ptr<char> tmpBuffer;

    // allocate a new kcp segment
    shared_ptr<IntcpSeg> createSeg(int size);
    char* encodeSeg(char *ptr, const IntcpSeg *seg);

    // flush pending data
    void flush();
    void flushWndProbe();
    void flushIntQueue();
    void flushIntBuf();
    void flushData();
    void flushHopRttAsk();
    
    int output(const void *data, int size, int dstRole);
    void updateRTT(IINT32 rtt);
    void updateHopRtt(IUINT32 ts);

    // after input
    void parseInt(IUINT32 rangeStart,IUINT32 rangeEnd,IUINT32 ts, IUINT32 wnd);

    // returns below zero for error
    int sendData(const char *buffer, IUINT32 start, IUINT32 end, IUINT32 tsEcho);

    void parseData(shared_ptr<IntcpSeg> newseg);
    
    void parseHopRttAsk(IUINT32 ts);
    
    void moveToRcvQueue();

//---------------------------------------------------------------------
// interface
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
    void request(IUINT32 rangeStart,IUINT32 rangeEnd);

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
    IUINT32 check(IUINT32 current);

    // user/upper level recv: returns size, returns below zero for EAGAIN
    int recv(char *buffer, int maxBufSize, IUINT32 *startPtr, IUINT32 *endPtr);

    static int judgeSegDst(const char *p, long size);

//---------------------------------------------------------------------
// rarely use
//---------------------------------------------------------------------
    // get how many packet is waiting to be sent
    int getWaitSnd();

    int getRwnd();

    // check the size of next message in the recv queue
    int peekSize();
};


#endif
