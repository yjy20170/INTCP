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
#include <iostream>//DEBUG

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

const IUINT32 INTCP_RTO_NDL = 10;        // no delay min rto
const IUINT32 INTCP_RTO_MIN = 20;        // normal min rto
const IUINT32 INTCP_RTO_DEF = 200;
const IUINT32 INTCP_RTO_MAX = 60000;
const float INTCP_RTO_FACTOR = 1.0;

const IUINT32 INTCP_CMD_INT = 80;         // cmd: interest 
const IUINT32 INTCP_CMD_PUSH = 81;        // cmd: push data
const IUINT32 INTCP_CMD_WASK = 83;        // cmd: window probe (ask)
const IUINT32 INTCP_CMD_WINS = 84;        // cmd: window size (tell)

const IUINT32 INTCP_ASK_SEND = 1;        // need to send INTCP_CMD_WASK
const IUINT32 INTCP_ASK_TELL = 2;        // need to send INTCP_CMD_WINS
const IUINT32 INTCP_WND_SND = 32;
const IUINT32 INTCP_WND_RCV = 128;       // must >= max fragment size
const IUINT32 INTCP_MTU_DEF = 1400; //EXPR 1400
const IUINT32 INTCP_ACK_FAST = 3;
const IUINT32 INTCP_INTERVAL = 5; //EXPR 100 -> 5
const IUINT32 INTCP_DEADLINK = 20;
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
    IUINT32 wnd;    //need send,2B //TODO for CC
    IUINT32 ts;        //need send,4B
    IUINT32 sn;        //need send,4B
    IUINT32 len;    //need send,4B
    IUINT32 resendts;
    IUINT32 rto;
    IUINT32 xmit;
    
    //intcp
    IUINT32 rangeStart;    //need send,4B 
    IUINT32 rangeEnd;    //need send,4B 
    
    char data[1];
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
	int xmit;
    
    int nodelay, nocwnd; // about rto caclulation
    int rx_rttval, rx_srtt, rx_rto, rx_minrto;
    int fastRetransThre, fastRetransCountLimit;
    IUINT32 snd_wnd, rcv_wnd, rmt_wnd, cwnd, ssthresh;
    
	IUINT32 current, updated, updateInterval, nextFlushTs;
    IUINT32 ts_probe, probe_wait, probe;

    //requester
    list<IntRange> int_queue;
    list<IntcpSeg*> int_buf;
    list<IntcpSeg*> rcv_buf;
    list<IntcpSeg*> rcv_queue;
    //responser
    list<IntRange> recvedInts;
    list<IntcpSeg*> snd_queue;

	// midnode solution 1 ---- one session has two unreliable TransCB
	// for requester
	// no timeout: interest in intlist will be directly output, thus no timeout detection.
	// still detects seq hole: when a seq hole is found, request it
	// for responser
	// no realignment: data will be directly push to rcv_queue
	// no PIT: unsatisfied interest will not be stored in recvedInts
	// bool isUnreliable;

	// midnode solution 2 ---- one TransCB
	bool isMidnode;
    //seqhole
    IUINT32 rightBound, byteRightBound, rightBoundTs;
    list<Hole> holes;
    
    void *user;
    int (*outputFunc)(const char *buf, int len, void *user, int dstRole);
	// set callback called by responseInterest
	int (*fetchDataFunc)(char *buf, IUINT32 start, IUINT32 end, void *user);
    int (*onUnsatInt)(IUINT32 start, IUINT32 end, void *user);
	// also called by responseInterest
    void* (*mallocFunc)(size_t);
    void (*freeFunc)(void *);

    char *tmpBuffer;

    void myFree(void *ptr);
    void* myMalloc(size_t size);

    // allocate a new kcp segment
    IntcpSeg* createSeg(int size);
    void deleteSeg(IntcpSeg *seg);
    char* encodeSeg(char *ptr, const IntcpSeg *seg);

    // flush pending data
    void flush();
    void flushWndProbe();
    void flushInt();
    void flushData();
    int output(const void *data, int size, int dstRole);
    void updateRTT(IINT32 rtt);

    // after input
    void parseInt(IUINT32 rangeStart,IUINT32 rangeEnd,IUINT32 ts);
	int responseInt(IUINT32 rangeStart, IUINT32 rangeEnd);
    // returns below zero for error
    int sendData(const char *buffer, IUINT32 start, IUINT32 end);

    void parseData(IntcpSeg *newseg);

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
			bool _isMidnode
	);
    // release kcp control object
    ~IntcpTransCB();

    // intcp user/upper level request
    void request(IUINT32 rangeStart,IUINT32 rangeEnd);

    // when you received a low level packet (eg. UDP packet), call it
    int input(char *data, int size);

    void notifyNewData(IUINT32 start, IUINT32 end, IUINT32 ts);

    // update state (call it repeatedly, every 10ms-100ms), or you can ask 
    // ikcp_check when to call it again (without ikcp_input/_send calling).
    // 'current' - current timestamp in millisec. 
    void update(IUINT32 current);

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
    // change MTU size, default is 1400
    int setMtu(int mtu);

    // set maximum window size: sndwnd=32, rcvwnd=32 by default
    int setWndSize(int sndwnd, int rcvwnd);

    int setInterval(int interval);

    // fastest: nodelay(kcp, 1, 20, 2, 1)
    // nodelay: 0:disable(default), 1:enable
    // interval: internal update timer interval in millisec, default is 100ms 
    // resend: 0:disable fast resend(default), 1:enable fast resend
    // nc: 0:normal congestion control(default), 1:disable congestion control
    int setNoDelay(int nodelay, int interval, int resend, int nc);

    // setup allocator
    void setAllocator(void* (*new_malloc)(size_t), void (*new_free)(void*));

    // get how many packet is waiting to be sent
    int getWaitSnd();

    int getRwnd();

    // check the size of next message in the recv queue
    int peekSize();
};


#endif