#include "./include/ikcp.h"
#undef LOG_LEVEL
#define LOG_LEVEL  DEBUG// SILENT//

#include <iostream>
using namespace std;

float bytesToMbit(int bytes){
    return float(bytes)*8/1000/1000;
}
int mbitToBytes(float mbit){
    return mbit/8*1000*1000;
}
//---------------------------------------------------------------------
// create a new IntcpTransCB
//---------------------------------------------------------------------
IntcpTransCB::IntcpTransCB(
        void *_user, 
        int (*_outputFunc)(const char *buf, int len, void *user, int dstRole),
        int (*_fetchDataFunc)(char *buf, IUINT32 start, IUINT32 end, void *user),
        int (*_onUnsatInt)(IUINT32 start, IUINT32 end, void *user),
        // bool _isUnreliable
        int _nodeRole
        ):
user(_user),
outputFunc(_outputFunc),
fetchDataFunc(_fetchDataFunc),
onUnsatInt(_onUnsatInt),
// isUnreliable(_isUnreliable), 
nodeRole(_nodeRole),
dataNextSn(0),
intNextSn(0),
rcvNxt(0),
cwnd(INTCP_CWND_MIN),
state(0),
srtt(0),
rttval(0),
rto(INTCP_RTO_DEF),
hopSrtt(0),
hopRttval(0),
nextFlushTs(0),
updated(0),
dataSnRightBound(-1),
dataByteRightBound(-1),
dataRightBoundTs(-1),
intSnRightBound(-1),
intByteRightBound(-1),
intRightBoundTs(-1),
ccState(INTCP_CC_SLOW_START),
ccDataLen(0),
dataOutputLimit(0),
// rmt_sndq_rest(INTCP_SNDQ_INIT),
sndQueueBytes(0),
intHopOwd(-1),
rmtSendRate(INTCP_SENDRATE_MIN),
intBufBytes(0),
lastCwndDecrTs(0),
lastThrpUpdateTs(0),
recvedBytesThisHRTT(0),
recvedBytesLastHRTT(0),
hasLossEvent(false),
thrpLastHRTT(-1),
conseqTimeout(0),
lastSendIntTs(0)
{
    stat.init();

    void *tmp = malloc(INTCP_MTU * 3);
    assert(tmp != NULL);
    tmpBuffer = shared_ptr<char>(static_cast<char*>(tmp));
}

// allocate a new intcp segment
shared_ptr<IntcpSeg> IntcpTransCB::createSeg(int size)
{
    void *tmp = malloc(sizeof(IntcpSeg)+size);
    assert(tmp != NULL);
    return shared_ptr<IntcpSeg>(static_cast<IntcpSeg*>(tmp));
}


// output segment, size include kcp header
int IntcpTransCB::output(const void *data, int size, int dstRole)
{
    // LOG(DEBUG, "size %d", size-INTCP_OVERHEAD);
    if (size == 0) return 0;
    return outputFunc((const char*)data, size, user, dstRole);
}

int IntcpTransCB::outputInt(IUINT32 rangeStart, IUINT32 rangeEnd){
    shared_ptr<IntcpSeg> segPtr = createSeg(0);
    segPtr->len = 0;
    segPtr->cmd = INTCP_CMD_INT;
    segPtr->rangeStart = rangeStart;
    segPtr->rangeEnd = rangeEnd;
    segPtr->ts = _getMillisec();
    segPtr->wnd = getSendRate();
    segPtr->sn = intNextSn++;
    encodeSeg(tmpBuffer.get(), segPtr.get());
    lastSendIntTs = segPtr->ts;
    return output(tmpBuffer.get(), INTCP_OVERHEAD, INTCP_RESPONDER);
}


//---------------------------------------------------------------------
// encodeSeg
//---------------------------------------------------------------------
char* IntcpTransCB::encodeSeg(char *ptr, const IntcpSeg *seg)
{
    ptr = encode8u(ptr, (IUINT8)seg->cmd);
    ptr = encode16u(ptr, seg->wnd);
    ptr = encode32u(ptr, seg->ts);
    ptr = encode32u(ptr, seg->sn);
    ptr = encode32u(ptr, seg->len);
    
    //intcp
    ptr = encode32u(ptr, seg->rangeStart);
    ptr = encode32u(ptr, seg->rangeEnd);
    
    return ptr;
}


//---------------------------------------------------------------------
// user/upper level recv: returns size, returns below zero for EAGAIN
//---------------------------------------------------------------------
int IntcpTransCB::recv(char *buffer, int maxBufSize, IUINT32 *startPtr, IUINT32 *endPtr)
{
    // int i=0;
    // for(list<IntcpSeg*>::iterator tmp=rcvQueue.begin(); tmp != rcvQueue.end(); tmp++) {
    //     LOG(DEBUG,"rcvQueue seg %d [%d,%d)",i++,(*tmp)->rangeStart,(*tmp)->rangeEnd);
    // }

    list<shared_ptr<IntcpSeg>>::iterator p;
    int recover = 0;
    shared_ptr<IntcpSeg> seg;

    if (rcvQueue.empty())
        return -1;
    //printf("111\n");
    if (rcvQueue.size() >= INTCP_WND_RCV)
        recover = 1;

    if(nodeRole == INTCP_MIDNODE){
        shared_ptr<IntcpSeg> firstSeg = *rcvQueue.begin();
        if(firstSeg->len <= maxBufSize){
            *startPtr = firstSeg->rangeStart;
            *endPtr = firstSeg->rangeEnd;
            memcpy(buffer, firstSeg->data, firstSeg->len);
            rcvQueue.pop_front();
        }
        //TODO else split
    } else {
        // copy seg->data in rcvQueue to buffer as much as possible
        *startPtr = *endPtr = (*rcvQueue.begin())->rangeStart;
        for (p = rcvQueue.begin(); p != rcvQueue.end(); ) {
            seg = *p;
            if(seg->len+ *endPtr - *startPtr > maxBufSize)
                break;
            if(*endPtr != seg->rangeStart)
                break;
            memcpy(buffer, seg->data, seg->len);
            buffer += seg->len;
            *endPtr += seg->len;
            
            rcvQueue.erase(p++);
        }
    }
    
    moveToRcvQueue();

    return 0;
}

//---------------------------------------------------------------------
// user/upper level send, returns below zero for error
//---------------------------------------------------------------------
int IntcpTransCB::sendData(const char *buffer, IUINT32 start, IUINT32 end)
{
    int len = end - start;
    // if(len>64){
    //     LOG(DEBUG,"%d %d",start,end);
    // }
    shared_ptr<IntcpSeg> seg;

    if (len <= 0) return -1;

    while(len>0) {
        int size = len > (int)INTCP_MSS ? (int)INTCP_MSS : len;
        seg = createSeg(size);
        assert(seg);
        if (seg == NULL) {
            return -2;
        }
        if (buffer && len > 0) {
            // LOG(DEBUG,"memcpy size %d",size);
            memcpy(seg->data, buffer, size);
        }
        seg->cmd = INTCP_CMD_PUSH;
        seg->len = size;
        seg->rangeStart = start;
        seg->rangeEnd = start+size;
        seg->wnd = 0;
        start += size;
        sndQueue.push_back(seg);
        sndQueueBytes += seg->len;
        LOG(TRACE, "sendData sn %d [%d,%d) ",seg->sn,seg->rangeStart,seg->rangeEnd);
        buffer += size;
        len -= size;
    }

    return 0;
}


//add (rangeStart,rangeEnd) to intQueue
int IntcpTransCB::request(IUINT32 rangeStart,IUINT32 rangeEnd){
    if(rangeEnd <= rangeStart){
        LOG(WARN,"rangeStart %d rangeEnd %d",rangeStart,rangeEnd);
        return -2;
    }
    if(intBufBytes >= INTCP_INTB_MAX){
        return -1;
    }
    IntRange intr;
    intr.startByte = rangeStart;
    intr.endByte = rangeEnd;
    intQueue.push_back(intr);
    return 0;
}
//---------------------------------------------------------------------
// update rtt(call when receive data)
//---------------------------------------------------------------------
void IntcpTransCB::updateRTT(IINT32 rtt, int xmit)
{
    if(xmit>1){
        LOG(TRACE,"retrans packet rtt %d",rtt);
    }
    if(rtt<=0){
        return;
    }
    if (srtt == 0) {
        srtt = rtt;
        rttval = rtt / 2;
        rto = _ibound_(INTCP_RTO_MIN, rtt * 3, INTCP_RTO_MAX);
        return;
    }
    int rttForUpdate=0, doUpdate=1;
    if (RTTscheme==INTCP_RTT_SCHM_MAXWND){
        // Scheme 1: max-window filter
        //NOTE this will result to a smaller rttVal during rtt oscillation
        // get old maxRtt
        int maxRttOld = -1;
        for(int r: rttQueue){
            maxRttOld = max(maxRttOld, r);
        }
        // update rtt queue
        rttQueue.push_back(rtt);
        while(rttQueue.size() > 5){//TODO more adaptive value?
            rttQueue.pop_front();
        }
        // get new maxRtt
        int maxRtt = -1;
        for(int r: rttQueue){
            maxRtt = max(maxRtt, r);
        }
        if(maxRttOld != maxRtt){
            rttForUpdate = maxRtt;
        }else{
            doUpdate = 0;
        }
    } else if (RTTscheme==INTCP_RTT_SCHM_EXPO){
        // Scheme 2: multiply rttval & srtt by a factor for the timeout interests
        if(xmit <= 1){
            rttForUpdate = rtt;
        }else{
            doUpdate = 0;
        }
    }

    //basic update logic
    if(doUpdate){
        long delta = rttForUpdate - srtt;
        if (delta < 0) delta = -delta;
        rttval = (3 * rttval + delta) / 4;
        srtt = (7 * srtt + rttForUpdate) / 8;
        if (srtt < 1) srtt = 1;
        IINT32 rtoTmp = srtt + _imax_(INTCP_UPDATE_INTERVAL, 4 * rttval);
        rto = _ibound_(INTCP_RTO_MIN, rtoTmp, INTCP_RTO_MAX);
    }

    LOG(TRACE,"rtt %d srtt %d val %d rto %d",rtt,srtt,rttval,rto);
}

void IntcpTransCB::updateHopRTT(IINT32 hop_rtt){
    if(hopSrtt ==0){
        hopSrtt = hop_rtt;
        hopRttval = hop_rtt/2; 
    }
    else{
        long delta = hop_rtt - hopSrtt;
        if (delta < 0) delta = -delta;
        hopRttval = (3 * hopRttval + delta) / 4;
        hopSrtt = (7 * hopSrtt + hop_rtt) / 8;
        if (hopSrtt < 1) hopSrtt = 1;
    }
}

void IntcpTransCB::detectIntHole(IUINT32 rangeStart, IUINT32 rangeEnd, IUINT32 sn){
    IUINT32 current = _getMillisec();
    if(intSnRightBound==-1 || current-intRightBoundTs>INTCP_SNHOLE_TIMEOUT){
        intSnRightBound = sn+1;
        intByteRightBound = rangeEnd;
        intRightBoundTs = current;
        intHoles.clear();
    }else{
        // locate the position of seg in intHoles
        list<Hole>::iterator iter,next;
        for(iter=intHoles.begin(); iter!=intHoles.end();iter=next){
            next=iter;next++;
            if(current-iter->ts>INTCP_SNHOLE_TIMEOUT){
                intHoles.erase(iter);
            } else if(sn >= iter->endSn){
                iter->count++;
                if(iter->count >= INTCP_SNHOLE_THRESHOLD){
                    if(iter->endByte - iter->startByte > (iter->endSn - iter->startSn)*INTCP_INT_RANGE_LIMIT){
                        LOG(TRACE, "---- Abnormal int hole [%d,%d) cur %u----", iter->startByte, iter->endByte, current);
                    } else {
                        stat.cntIntHole++;
                        LOG(TRACE,"---- int hole [%d,%d) cur %u----", iter->startByte, iter->endByte, current);
                        parseInt(iter->startByte, iter->endByte);
                    }
                    intHoles.erase(iter);
                }
            } else if(sn >= iter->startSn){
                if(sn == iter->startSn){
                    if(sn == iter->endSn-1){ // hole is fixed
                        intHoles.erase(iter);
                    } else {
                        iter->startSn++;
                        iter->startByte = rangeEnd;
                    }
                }else if(sn == iter->endSn-1){
                    iter->endSn--;
                    iter->endByte = rangeStart;
                    iter->count++;
                }else{
                    Hole newHole;
                    newHole.count = iter->count;
                    newHole.startSn = sn+1;
                    newHole.endSn = iter->endSn;
                    newHole.startByte = rangeEnd;
                    newHole.endByte = iter->endByte;
                    newHole.ts = iter->ts;
                    intHoles.insert(next, newHole);

                    iter->endSn = sn;
                    iter->endByte = rangeStart;
                    iter->count++;
                }
            } else { // segPtr->sn < iter->startSn
                // for this hole and subsequent holes, all hole.start > sn
                break;
            }
        }
        if(sn >= intSnRightBound){
            if(sn > intSnRightBound && (rangeStart>intByteRightBound)){
                // add a new hole
                Hole newHole;
                newHole.startSn = intSnRightBound;
                newHole.endSn = sn;
                newHole.startByte = intByteRightBound;
                newHole.endByte = rangeStart;
                newHole.ts = current;
                newHole.count = 1;
                intHoles.push_back(newHole);
            }
            intSnRightBound = sn+1;
            intByteRightBound = _imax_(intByteRightBound,rangeEnd);
            intRightBoundTs = current;
        }
        
    }
    if(!intHoles.empty()){
        char tmp[100];
        string str;
        for(auto ho:intHoles){
            snprintf(tmp,100,"   [ st %d end %d bSt %d bEnd %d ]",ho.startSn,ho.endSn,ho.startByte,ho.endByte);
            str += tmp;
        }
        LOG(TRACE,"sn %d intHoles: %ld %s",
                sn,intHoles.size(),str.c_str());
    }
}
void IntcpTransCB::parseInt(IUINT32 rangeStart, IUINT32 rangeEnd){
    //TODO priority
    if(rangeEnd <= rangeStart){
        LOG(TRACE,"rangeEnd <= rangeStart");
        return;
    }

    IUINT32 sentEnd=rangeStart;
    if(nodeRole != INTCP_REQUESTER) {
        // first, try to fetch data
        IUINT32 segStart, segEnd;
        int fetchLen;
        for(segStart = rangeStart; segStart < rangeEnd; segStart+=INTCP_MSS){
            segEnd = _imin_(rangeEnd, segStart+INTCP_MSS);
            fetchLen = fetchDataFunc(tmpBuffer.get(), segStart, segEnd, user);
            sentEnd = segStart+fetchLen;
            if(fetchLen==0)
                break;
            // push fetched data(less than mtu) to sndQueue
            sendData(tmpBuffer.get(),segStart,segStart+fetchLen);
            // if this seg is not completed due to data miss
            if(fetchLen<segEnd-segStart){
                break;
            }
        }
    }
    
    // rest range
    if(sentEnd<rangeEnd){
        //NOTE in midnode, if cache has [3,10], interest is [0,10], the whole cache is wasted;
        if(nodeRole == INTCP_RESPONDER){
            // append interest to pendingInts
            if(rangeEnd <= rangeStart){
                LOG(WARN,"rangeStart %d rangeEnd %d",rangeStart,rangeEnd);
                return;
            }
            IntRange ir;
            ir.ts = _getMillisec();
            ir.startByte = sentEnd;
            ir.endByte = rangeEnd;
            pendingInts.push_back(ir);
            LOG(TRACE,"unsat [%d,%d)",sentEnd,rangeEnd);
            onUnsatInt(sentEnd, rangeEnd, user);
        }else if(nodeRole==INTCP_REQUESTER){
            //TODO should be pushed to intQueue for shaping?

            // plan A
            // shared_ptr<IntcpSeg> newseg = createSeg(0);
            // newseg->len = 0;
            // newseg->cmd = INTCP_CMD_INT;
            // newseg->xmit = 0;
            // newseg->ts = ts;
            // newseg->rangeStart = sentEnd;
            // newseg->rangeEnd = rangeEnd;
            // intBuf.push_back(newseg); 

            // plan B
            // request(sentEnd, rangeEnd);

            // plan C
            // neither pushed to intQueue nor to intBuf, send it directly
            outputInt(sentEnd, rangeEnd);
            // rmt_sndq_rest -= segPtr->rangeEnd - segPtr->rangeStart;
        } else { //INTCP_MIDNODE
            request(sentEnd, rangeEnd);
        }
    }
}

void IntcpTransCB::notifyNewData(const char *buffer, IUINT32 dataStart, IUINT32 dataEnd){
    if(pendingInts.empty())
        return;
    list<IntRange>::iterator p, next;
    IntcpSeg* seg;
    for (p = pendingInts.begin(); p != pendingInts.end(); p = next) {
        next = p; next++;
        int intStart = p->startByte, intEnd = p->endByte, ts = p->ts;
        // check if the union is not empty
        if (_itimediff(intStart,dataEnd) <0 && _itimediff(intEnd,dataStart) >0){
            IUINT32 maxStart = _imax_(intStart, dataStart);
            IUINT32 minEnd = _imin_(intEnd, dataEnd);
            LOG(TRACE,"satisfy pending int: [%d,%d)",maxStart,minEnd);
            sendData(buffer+maxStart-dataStart, maxStart, minEnd);
            if(maxStart==intStart && minEnd==intEnd) {
                pendingInts.erase(p);
            } else if (minEnd==intEnd) {
                // partly sent
                p->endByte = maxStart;
            } else {
                p->startByte = minEnd;
                if (maxStart!=intStart) {
                    IntRange ir;
                    ir.ts = ts;
                    ir.startByte = intStart;
                    ir.endByte = maxStart;
                    pendingInts.insert(p,ir);
                }
            }
        }
    }
}

//---------------------------------------------------------------------
// parse data
//---------------------------------------------------------------------
bool IntcpTransCB::detectDataHole(IUINT32 rangeStart, IUINT32 rangeEnd, IUINT32 sn){        //return true when find a new hole
    bool found_new_loss = false;
    IUINT32 current = _getMillisec();
    if(dataSnRightBound==-1 || current-dataRightBoundTs>INTCP_SNHOLE_TIMEOUT){
        dataSnRightBound = sn+1;
        dataByteRightBound = rangeEnd;
        dataRightBoundTs = current;
        dataHoles.clear();
    }else{
        // locate the position of seg in dataHoles
        list<Hole>::iterator iter,next;
        for(iter=dataHoles.begin(); iter!=dataHoles.end();iter=next){
            next=iter;next++;
            if(current-iter->ts>INTCP_SNHOLE_TIMEOUT){
                dataHoles.erase(iter);
            } else if(sn >= iter->endSn){
                iter->count++;
                if(iter->count >= INTCP_SNHOLE_THRESHOLD){
                    found_new_loss = true;
                    if(iter->endByte - iter->startByte > (iter->endSn - iter->startSn)*INTCP_MSS){
                        LOG(TRACE, "---- Abnormal data hole [%u,%u) [%u,%u) t %u----", iter->startSn,iter->endSn,iter->startByte, iter->endByte, current);
                        stat.cntDataHole++;
                    } else {
                        LOG(TRACE,"---- data hole [%u,%u) [%u,%u) t %u----", iter->startSn,iter->endSn,iter->startByte, iter->endByte, current);
                        parseInt(iter->startByte,iter->endByte);
                        list<shared_ptr<IntcpSeg>>::iterator iterInt;
                        // if the range of this hole could cover an interest in intBuf, modify the ts of interest
                        for(iterInt=intBuf.begin();iterInt!=intBuf.end();iterInt++){
                            if(max(iter->startByte,(*iterInt)->rangeStart) < min(iter->endByte,(*iterInt)->rangeEnd)){
                                //------------------------------
                                // update intBuf
                                //------------------------------
                                if(iter->startByte <= (*iterInt)->rangeStart){
                                    if(iter->endByte >= (*iterInt)->rangeEnd){    //range completely received
                                        (*iterInt)->ts = _getMillisec();
                                    }else{
                                        shared_ptr<IntcpSeg> newseg = createSeg(0);
                                        memcpy(newseg.get(), (*iterInt).get(), sizeof(IntcpSeg));
                                        newseg->rangeStart = iter->endByte;
                                        // newseg->rttUpdate = true;
                                        (*iterInt)->rangeEnd = iter->endByte;
                                        (*iterInt)->ts = _getMillisec();

                                        intBuf.insert(iterInt,newseg);
                                        iterInt++;
                                    }
                                } else if(iter->endByte >= (*iterInt)->rangeEnd){
                                    shared_ptr<IntcpSeg> newseg = createSeg(0);
                                    memcpy(newseg.get(), (*iterInt).get(), sizeof(IntcpSeg));
                                    newseg->rangeStart = iter->startByte;
                                    // newseg->rttUpdate = true;
                                    (*iterInt)->rangeEnd = iter->startByte;
                                    newseg->ts = _getMillisec();
                                    intBuf.insert(iterInt,newseg);
                                    iterInt++;
                                }else{
                                    shared_ptr<IntcpSeg> newseg = createSeg(0);
                                    memcpy(newseg.get(), (*iterInt).get(), sizeof(IntcpSeg));
                                    newseg->rangeStart = iter->endByte;
                                    // newseg->rttUpdate = true; keep the same as the previous interest
                                    intBuf.insert(iterInt,newseg);

                                    newseg = createSeg(0);
                                    memcpy(newseg.get(), (*iterInt).get(), sizeof(IntcpSeg));
                                    newseg->rangeStart = iter->startByte;
                                    newseg->rangeEnd = iter->endByte;
                                    newseg->ts = _getMillisec();
                                    // newseg->rttUpdate = true;
                                    intBuf.insert(iterInt,newseg);

                                    (*iterInt)->rangeEnd = iter->startByte;
                                    iterInt++;
                                    iterInt++;
                                }
                            }
                        }
                    }
                    dataHoles.erase(iter);
                }
            } else if(sn >= iter->startSn){
                if(sn == iter->startSn){
                    if(sn == iter->endSn-1){ // hole is fixed
                        dataHoles.erase(iter);
                    } else {
                        iter->startSn++;
                        iter->startByte = rangeEnd;
                    }
                }else if(sn == iter->endSn-1){
                    iter->endSn--;
                    iter->endByte = rangeStart;
                    iter->count++;
                }else{
                    Hole newHole;
                    newHole.count = iter->count;
                    newHole.startSn = sn+1;
                    newHole.endSn = iter->endSn;
                    newHole.startByte = rangeEnd;
                    newHole.endByte = iter->endByte;
                    newHole.ts = iter->ts;
                    dataHoles.insert(next, newHole);

                    iter->endSn = sn;
                    iter->endByte = rangeStart;
                    iter->count++;
                }
            } else { // segPtr->sn < iter->start
                // for this hole and subsequent holes, all hole.start > sn
                break;
            }
        }
        if(sn >= dataSnRightBound){
            if(sn > dataSnRightBound && (rangeStart>dataByteRightBound)){
                // add a new hole
                Hole newHole;
                newHole.startSn = dataSnRightBound;
                newHole.endSn = sn;
                newHole.startByte = dataByteRightBound;
                newHole.endByte = rangeStart;
                LOG(TRACE,"---- data hole [%d,%d) cur %u----", newHole.startByte, newHole.endByte, current);
                newHole.ts = current;
                newHole.count = 1;
                dataHoles.push_back(newHole);
            }
            dataSnRightBound = sn+1;
            dataByteRightBound = _imax_(dataByteRightBound,rangeEnd);
            dataRightBoundTs = current;
        }
        
    }
    if(!dataHoles.empty()){
        char tmp[100];
        string str;
        for(auto ho:dataHoles){
            snprintf(tmp,100,"   [ st %d end %d bSt %d bEnd %d ]",ho.startSn,ho.endSn,ho.startByte,ho.endByte);
            str += tmp;
        }
        LOG(TRACE,"sn %d dataHoles: %ld %s",
                sn,dataHoles.size(),str.c_str());
    }
    return found_new_loss;
}



void IntcpTransCB::parseData(shared_ptr<IntcpSeg> dataSeg)
{
    if(nodeRole == INTCP_REQUESTER){
        list<shared_ptr<IntcpSeg>>::iterator intIter, intNext;
        //in requester, need to delete range of intBuf
        for (intIter = intBuf.begin(); intIter != intBuf.end(); intIter = intNext) {
            shared_ptr<IntcpSeg> intSeg = *intIter;
            intNext = intIter; intNext++;
            // if (_itimediff(sn, intSeg->rangeStart) < 0){
            //     break;
            // }
            if (dataSeg->rangeStart < intSeg->rangeEnd && dataSeg->rangeEnd > intSeg->rangeStart) {
                LOG(TRACE,"[%d,%d) rtt %d current %u xmit %d",dataSeg->rangeStart,dataSeg->rangeEnd,
                        _getMillisec()-intSeg->ts, _getMillisec(), intSeg->xmit);

                // if(intSeg->rttUpdate){
                // // if(true){
                //     updateRTT(_itimediff(_getMillisec(), intSeg->ts));
                //     intSeg->rttUpdate = false;
                // }

                //-------------------------------
                // insert [the intersection of seg and interest] into rcvBuf
                //-------------------------------
                int intsecStart = _imax_(intSeg->rangeStart,dataSeg->rangeStart);
                int intsecEnd = _imin_(intSeg->rangeEnd,dataSeg->rangeEnd);
                shared_ptr<IntcpSeg> intsecDataSeg = createSeg(intsecEnd-intsecStart);
                intsecDataSeg->rangeStart = intsecStart;
                intsecDataSeg->rangeEnd = intsecEnd;
                intsecDataSeg->len = intsecEnd-intsecStart;
                memcpy(intsecDataSeg->data, dataSeg->data+intsecStart-dataSeg->rangeStart,
                        intsecEnd-intsecStart);

                //NOTE pass information to app layer
                IUINT32 cur_tmp = _getMillisec();
                // LOG(DEBUG,"xmit %u rto %u rcvTime %u",intSeg->xmit,intSeg->rto,cur_tmp);
                memcpy(intsecDataSeg->data+sizeof(IUINT32), &intSeg->xmit, sizeof(IUINT32));
                memcpy(intsecDataSeg->data+sizeof(IUINT32)*2, &cur_tmp, sizeof(IUINT32));
                // memcpy(intsecDataSeg->data+sizeof(IUINT32)*3, &intSeg->firstTs, sizeof(IUINT32));
                
                if(rcvBuf.empty()){
                    rcvBuf.push_back(intsecDataSeg);
                }else{
                    int found=0;
                    list<shared_ptr<IntcpSeg>>::iterator dataIter;
                    for (dataIter = rcvBuf.end(); dataIter != rcvBuf.begin(); ) {
                        --dataIter;
                        shared_ptr<IntcpSeg> iterSeg = *dataIter;
                        if (_itimediff(intsecDataSeg->rangeStart, iterSeg->rangeEnd) >= 0) {
                            found = 1;
                            break;
                        }
                    }
                    if(found==1){
                        rcvBuf.insert(++dataIter,intsecDataSeg);
                    }else{
                        rcvBuf.insert(dataIter,intsecDataSeg);
                    }
                }

                //------------------------------
                // update intBuf
                //------------------------------
                // intSeg->rttUpdate = false;
                intBufBytes -= intsecEnd - intsecStart;
                stat.recvedINTCP += intsecEnd - intsecStart;
                conseqTimeout = 0;
                if(dataSeg->rangeStart <= intSeg->rangeStart){
                    if(dataSeg->rangeEnd >= intSeg->rangeEnd){    //range completely received
                        updateRTT(_itimediff(_getMillisec(), intSeg->ts), intSeg->xmit);
                        intBuf.erase(intIter);
                    }
                    else{
                        intSeg->rangeStart = dataSeg->rangeEnd;
                    }
                } else if(dataSeg->rangeEnd >= intSeg->rangeEnd){
                    intSeg->rangeEnd = dataSeg->rangeStart;
                }else{
                    //intSeg->rangeEnd = sn;
                    shared_ptr<IntcpSeg> newseg = createSeg(0);
                    memcpy(newseg.get(), intSeg.get(), sizeof(IntcpSeg));
                    intSeg->rangeEnd = dataSeg->rangeStart;
                    newseg->rangeStart = dataSeg->rangeEnd;

                    intBuf.insert(intIter,newseg);
                }
            }
        }
    } else {
        shared_ptr<IntcpSeg> segToForward = createSeg(dataSeg->len);
        //TODO copy char[] pointer??
        memcpy(segToForward.get(),dataSeg.get(),INTCP_OVERHEAD+dataSeg->len);
        sndQueue.push_back(segToForward);
        sndQueueBytes += segToForward->len;
        // receiving by upper layer delete this seg, 
        // output also delete it, so we need two seg
        // in sendData(), the sn will be rewrite
        // sendData(data, rangeStart, rangeEnd);
        rcvBuf.push_back(dataSeg);
    }

    moveToRcvQueue();
}

//reordering in requester: queueing in order of interest
// (suppose interest is in order now)
// move available data from rcvBuf -> rcvQueue
void IntcpTransCB::moveToRcvQueue(){
    
    while (!rcvBuf.empty()) {
        if(nodeRole == INTCP_MIDNODE){
            // LOG(DEBUG,"rq size %ld rw %u",rcvQueue.size(), INTCP_WND_RCV);
            if(rcvQueue.size() < INTCP_WND_RCV){
                rcvQueue.splice(rcvQueue.end(),rcvBuf,rcvBuf.begin(),rcvBuf.end());
            }else{
                break;
            }
        }else{
            shared_ptr<IntcpSeg> seg = *rcvBuf.begin();
            if (seg->rangeStart == rcvNxt && rcvQueue.size() < INTCP_WND_RCV) {
                rcvNxt = seg->rangeEnd;
                rcvQueue.splice(rcvQueue.end(),rcvBuf,rcvBuf.begin());
            } else {
                break;
            }
        }
    }
}
//---------------------------------------------------------------------
// input data
//---------------------------------------------------------------------
int IntcpTransCB::input(char *data, int size)
{
    if (data == NULL || (int)size < (int)INTCP_OVERHEAD) return -1;

    // when receiving udp packet, we use judgeDst() to get info from the 
    // first intcp seg, to decide which IntcpSess it should be inputed to.
    // if multiple intcp segs are concatenated in this single udp packet,
    // and they have different dst, there will be error.
    // so, now we only allow one intcp seg per input().
    // while (1) {
    IUINT32 ts, sn, len;
    IUINT32 rangeStart,rangeEnd;    //intcp
    IUINT16 wnd;
    IUINT8 cmd;
    shared_ptr<IntcpSeg> seg;


    char *dataOrg = data;
    long sizeOrg = size;
    while(1){
        IUINT32 current = _getMillisec();
        if (size < (int)INTCP_OVERHEAD)
            break;
        data = decode8u(data, &cmd);
        data = decode16u(data, &wnd);
        data = decode32u(data, &ts);
        data = decode32u(data, &sn);
        data = decode32u(data, &len);
        // if(len+INTCP_OVERHEAD<size){
        //     LOG(WARN, "input size %d > seg size %d",size,len+INTCP_OVERHEAD);
        // } 
        data = decode32u(data, &rangeStart);
        data = decode32u(data, &rangeEnd);
        size -= INTCP_OVERHEAD;

        if ((long)size < (long)len || (int)len < 0) return -2;
        
        if (cmd != INTCP_CMD_PUSH && cmd != INTCP_CMD_INT) 
            return -3;

        if(cmd==INTCP_CMD_INT){
            intHopOwd = _getMillisec() - ts;
            rmtSendRate = float(wnd)/100;
            LOG(TRACE, "recv int [%d,%d)",rangeStart,rangeEnd);
            if(!(rangeStart==0 && rangeEnd==0)){
                detectIntHole(rangeStart,rangeEnd,sn);
                parseInt(rangeStart,rangeEnd);
            }
        } else if (cmd == INTCP_CMD_PUSH) {
            LOG(TRACE, "input data sn %d [%d,%d)", sn, rangeStart,rangeEnd);

            //TODO avoid memcpy
            // if (isMidnode) {
            //     decode16u(dataOrg+sizeof(cmd),&wnd);
            //     outputFunc(dataOrg, sizeOrg, user, INTCP_REQUESTER);
            // }

            // rmt_sndq_rest = wnd*INTCP_MSS;//TODO for midnode, ignore this part

            // LOG(TRACE,"%d",rmt_sndq_rest);
            if(current>ts){
                updateHopRTT(current-ts);
            }else{
                LOG(WARN,"_getMillisec()>ts");
            }
            if(hopSrtt!=0){ //only begin calculating throughput when hoprtt exists
                recvedBytesThisHRTT+=len;
                stat.recvedUDP += len;
                if(lastThrpUpdateTs==0)
                    lastThrpUpdateTs = current;
                if(_itimediff(current,lastThrpUpdateTs)>hopSrtt){
                    recvedBytesLastHRTT = recvedBytesThisHRTT;
                    thrpLastHRTT = bytesToMbit(recvedBytesThisHRTT)/hopSrtt*1000;
                    LOG(TRACE,"receive rate = %.2fMbps",bytesToMbit(recvedBytesLastHRTT)*1000/hopSrtt);
                    recvedBytesThisHRTT = 0;
                    lastThrpUpdateTs = current;
                }
            }
            updateCwnd(len);
            if(current - lastSendIntTs > hopSrtt*0.9){
                outputInt(0,0);
            }

            bool foundDataHole = detectDataHole(rangeStart,rangeEnd,sn);
            hasLossEvent = hasLossEvent || foundDataHole;

            seg = createSeg(len);
            seg->cmd = cmd;
            seg->wnd = wnd;
            // seg->ts = ts;
            // seg->sn = sn;
            seg->len = len;
            seg->rangeStart = rangeStart;
            seg->rangeEnd = rangeEnd;
            memcpy(seg->data, data, len);

            parseData(seg);
        } else {
            return -3;
        }

        data += len;
        size -= len;
    }

    return 0;
}

//---------------------------------------------------------------------
// flush
//---------------------------------------------------------------------

void IntcpTransCB::flushIntQueue(){
    while(!intQueue.empty()){
        shared_ptr<IntcpSeg> newseg = createSeg(0);
        assert(newseg);
        newseg->len = 0;
        newseg->sn = 0;
        newseg->cmd = INTCP_CMD_INT;
        // newseg->rttUpdate = true;
        newseg->xmit = 0;
        
        bool first = true;
        //NOTE assume that rangeEnd of interest in intQueue is in order
        for(list<IntRange>::iterator iter=intQueue.begin();iter!=intQueue.end();){
            if(first){
                newseg->rangeStart = iter->startByte;
                newseg->rangeEnd = _imin_(iter->endByte, newseg->rangeStart+INTCP_INT_RANGE_LIMIT);
                first = false;
            } else {
                if(iter->startByte == newseg->rangeEnd){
                    LOG(TRACE,"%u %u %u %u",newseg->rangeStart,newseg->rangeEnd,iter->startByte,iter->endByte);
                    // newseg->rangeStart = _imin_(iter->start,newseg->rangeStart);
                    newseg->rangeEnd = _imin_(iter->endByte,
                            newseg->rangeStart+INTCP_INT_RANGE_LIMIT);
                } else {
                    break;
                }
            }
            if(iter->endByte <= newseg->rangeEnd){
                intQueue.erase(iter++);
            } else {
                iter->startByte = newseg->rangeEnd;
                break;
            }
        }
        // intRangeLimit -= newseg->rangeEnd-newseg->rangeStart;
        intBufBytes += newseg->rangeEnd-newseg->rangeStart;
        intBuf.push_back(newseg);
    }
}

void IntcpTransCB::flushIntBuf(){
    // if(nodeRole==INTCP_REQUESTER && rmt_sndq_rest<= 0){
    //     return;
    // }
    // intOutputLimit += int(float(rmt_sndq_rest)/srtt*INTCP_UPDATE_INTERVAL/1000);
    char *sentEnd=tmpBuffer.get();
    int sizeToSend=0;
    // from intBuf to udp
    list<shared_ptr<IntcpSeg>>::iterator p,next;

    int cntAll=0,cntTimeout=0,cntRetransed=0;

    // bool reach_limit = false;
    for (p = intBuf.begin(); p != intBuf.end(); p=next) {
        cntAll++;
        next=p;next++;
        IUINT32 current = _getMillisec();
        shared_ptr<IntcpSeg> segPtr = *p;
        int needsend = 0;
        if(nodeRole == INTCP_MIDNODE){
            needsend = 1;
        } else {
            // RTO mechanism
            if (segPtr->xmit >= 2) {cntRetransed++;}
            if (segPtr->xmit == 0) {
                needsend = 1;
            // } else if (_itimediff(current, segPtr->resendts) >= 0) {
            } else {
                //NOTE RTO function: segRto=f(rto, xmit)
                IUINT32 segRto = rto*( pow(1.5,segPtr->xmit-1) +1);// + 1000;
                if (_itimediff(current, segPtr->ts) >= segRto) {
                    if (segPtr->xmit >= INTCP_DEADLINK || segRto>=INTCP_RTO_MAX) {
                        LOG(DEBUG,"xmit %d rto %u",segPtr->xmit,segRto);
                        state = -1;
                        LOG(ERROR, "dead link");
                        abort();
                    }
                    hasLossEvent = true;
                    cntTimeout++;
                    LOG(TRACE,"----- Timeout [%d,%d) xmit %d cur %u rto %d -----",
                            segPtr->rangeStart, segPtr->rangeEnd, segPtr->xmit, _getMillisec(),rto);
                    needsend = 1;
                    stat.xmit++;
                }
            }
        }

        if (needsend) {
            //clear hole
            if(nodeRole != INTCP_MIDNODE){
                list<Hole>::iterator iter,next;
                for(iter=dataHoles.begin(); iter!=dataHoles.end();iter=next){
                    next=iter;next++;
                    IUINT32 maxStart = _imax_(segPtr->rangeStart,iter->startByte);
                    IUINT32 minEnd = _imin_(segPtr->rangeEnd, iter->endByte);
                    if(maxStart < minEnd){
                        LOG(TRACE, "RTO[%d,%d) cover hole [%d,%d)", segPtr->rangeStart, segPtr->rangeEnd, iter->startByte, iter->endByte);
                        if(maxStart == iter->startByte){
                            if(minEnd == iter->endByte){ // hole is fixed
                                dataHoles.erase(iter);
                            } else {
                                iter->startByte = minEnd;
                            }
                        }else if(minEnd == iter->endByte){
                            iter->endByte = maxStart;
                        }else{
                            Hole newHole;
                            newHole.count = iter->count;
                            newHole.startSn = iter->startSn;
                            newHole.endSn = iter->endSn;
                            newHole.startByte = minEnd;
                            newHole.endByte = iter->endByte;
                            newHole.ts = iter->ts;
                            dataHoles.insert(next, newHole);

                            iter->endByte = maxStart;
                        }
                    }
                }
            }
            // if(nodeRole==INTCP_REQUESTER){
            //     // rmt_sndq_rest -= segPtr->rangeEnd - segPtr->rangeStart;
            //     if(intOutputLimit<segPtr->len){
            //         LOG(TRACE,"intOutputLimit %d bytes seglen %d qsize %ld",intOutputLimit,segPtr->len,sndQueue.size());
            
            //         reach_limit = true;
            //         break;
            //     }else{
            //         intOutputLimit -= segPtr->rangeEnd - segPtr->rangeStart;
            //     }
            // }
            outputInt(segPtr->rangeStart, segPtr->rangeEnd);
            segPtr->xmit++;
            segPtr->ts = current;


            if(nodeRole == INTCP_MIDNODE){
                intBufBytes -= (*p)->rangeEnd - (*p)->rangeStart;
                intBuf.erase(p);
            }
            // if(nodeRole==INTCP_REQUESTER && rmt_sndq_rest<= 0){
            //     break;
            // }
        }
    }
    // if(!reach_limit){
    //     intOutputLimit = 0;//min();
    // }
    LOG(TRACE,"RTO %d %d/%d/%d",rto,cntTimeout,cntRetransed,cntAll);
    stat.cntTimeout += cntTimeout;
    if(cntTimeout>0){
        conseqTimeout++;
    }
    if(RTTscheme==INTCP_RTT_SCHM_EXPO && cntTimeout>0 && conseqTimeout<10){
        srtt = srtt * INTCP_RTO_EXPO;
        rto = rto * INTCP_RTO_EXPO;
    }
}

// sndQueue -> send straightforward;
void IntcpTransCB::flushData(){
    //TODO CC -- cwnd/sendingRate; design token bucket
    dataOutputLimit += mbitToBytes(rmtSendRate*INTCP_UPDATE_INTERVAL/1000);
    LOG(TRACE,"dataOutputLimit %d bytes %ld",dataOutputLimit,sndQueue.size());
    //int dataOutputLimit = 65536;

    char *sentEnd=tmpBuffer.get();
    int sizeToSend=0;

    bool reach_limit = false;
    list<shared_ptr<IntcpSeg>>::iterator p, next;
    shared_ptr<IntcpSeg> segPtr;
    for (p = sndQueue.begin(); p != sndQueue.end(); p=next){
        next = p; next++;
        segPtr = *p;
        if(dataOutputLimit<segPtr->len){
            LOG(TRACE,"dataOutputLimit %d bytes seglen %d qsize %ld",dataOutputLimit,segPtr->len,sndQueue.size());
    
            reach_limit = true;
            break;
        }else{
            dataOutputLimit -= segPtr->len;
        }

        sizeToSend = (int)(sentEnd - tmpBuffer.get());
        if (sizeToSend + (INTCP_OVERHEAD + segPtr->len) > INTCP_MTU) {
            output(tmpBuffer.get(), sizeToSend, INTCP_REQUESTER);
            sentEnd = tmpBuffer.get();
        }

        segPtr->sn = dataNextSn++;
        LOG(TRACE,"sn %d [%d,%d) cur %u",segPtr->sn,segPtr->rangeStart,segPtr->rangeEnd,_getMillisec());
        segPtr->ts = _getMillisec() - intHopOwd;

        // make sure the midnode doesn't change wnd from responder;
        //TODO if it's from cache, wnd=0
        if(nodeRole==INTCP_RESPONDER){
            //TODO wnd in DATA is not used currently
            segPtr->wnd = IUINT16((INTCP_SNDQ_MAX - _imin_(INTCP_SNDQ_MAX,sndQueueBytes))/INTCP_MSS);
            LOG(TRACE,"%d %u",sndQueueBytes,segPtr->wnd);
        }
        
        sentEnd = encodeSeg(sentEnd, segPtr.get());
        memcpy(sentEnd, segPtr->data, segPtr->len);
        sentEnd += segPtr->len;
        sndQueueBytes -= segPtr->len;
        sndQueue.erase(p);
    }
    //if cwnd is not enough for data, the remain wnd can be used for next loop
    if(!reach_limit){
        dataOutputLimit = 0;//min();
    }
        
    // if(cwnd!=0) {
    //     LOG(DEBUG,"%d %d",rmt_cwnd,reach_limit);
    // }
    // flush remain segments
    sizeToSend = (int)(sentEnd - tmpBuffer.get());
    if (sizeToSend > 0) {
        output(tmpBuffer.get(), sizeToSend, INTCP_REQUESTER);
    }
}

void IntcpTransCB::flush(){
    // 'update' haven't been called. 
    if (updated == 0) return;
    
    if(nodeRole != INTCP_RESPONDER){
        flushIntQueue();
        flushIntBuf();
    }
    if(nodeRole != INTCP_REQUESTER){
        flushData();
    }
}


//---------------------------------------------------------------------
// update state (call it repeatedly, every 10ms-100ms), or you can ask 
// check when to call it again (without input/_send calling).
// 'current' - current timestamp in millisec. 
//---------------------------------------------------------------------
void IntcpTransCB::update()
{
    IUINT32 current = _getMillisec();
    if(current-stat.lastPrintTs>1000){
        if(nodeRole==INTCP_REQUESTER){
            LOG(DEBUG,"%4d %d C %4u ↑%.1f ↓%.1f+%.1f rB %ld T %d H %d",
                    srtt,hopSrtt,
                    cwnd,
                    float(getSendRate())/100,
                    bytesToMbit(stat.recvedINTCP)*1000/(current-stat.lastPrintTs),
                    bytesToMbit(stat.recvedUDP-stat.recvedINTCP)*1000/(current-stat.lastPrintTs),
                    rcvBuf.size(),
                    stat.cntTimeout,stat.cntDataHole);
            //NOTE
            printf("  %4ds %.2f Mbits/sec receiver\n",
                    (current-stat.startTs)/1000,
                    bytesToMbit(stat.recvedINTCP)*1000/(current-stat.lastPrintTs)
            );
        }
        if(nodeRole==INTCP_MIDNODE){
            LOG(DEBUG,"hr %d cwnd %u sndr %.2f thrp %.2f rB %4ld dh %d",
                    hopSrtt,
                    cwnd,
                    float(getSendRate())/100,
                    bytesToMbit(stat.recvedUDP)*1000/(current-stat.lastPrintTs),
                    rcvBuf.size(),
                    stat.cntDataHole);
        }
        if(nodeRole!=INTCP_REQUESTER){
            LOG(DEBUG,"%d| %4d rmtSndr %.2f sndq %d ih %d",
                    stat.ssid, (current-stat.startTs)/1000,
                    rmtSendRate, sndQueueBytes/INTCP_MSS,
                    stat.cntIntHole);
        }
        stat.reset();
    }
    if (updated == 0) {
        updated = 1;
        nextFlushTs = current;
    }

    IINT32 slap = _itimediff(current, nextFlushTs);

    if (slap>0 || slap<-10000){
        // LOG(DEBUG,"iq %ld ib %ld pit %ld sq %ld rb %ld rq %ld",
        //         intQueue.size(), intBuf.size(),pendingInts.size(),
        //         sndQueue.size(),rcvBuf.size(),rcvQueue.size());
        flush();
        if (slap >= INTCP_UPDATE_INTERVAL || slap < -10000) {
            nextFlushTs = current + INTCP_UPDATE_INTERVAL;
        } else {
            nextFlushTs = nextFlushTs + INTCP_UPDATE_INTERVAL;
        }
    }
}

//---------------------------------------------------------------------
// Determine when should you invoke update:
// returns when you should invoke update in millisec, if there 
// is no input/_send calling. you can call update in that
// time, instead of call update repeatly.
// Important to reduce unnacessary update invoking. use it to 
// schedule update (eg. implementing an epoll-like mechanism, 
// or optimize update when handling massive kcp connections)
//---------------------------------------------------------------------
IUINT32 IntcpTransCB::check()
{
    IUINT32 currentU = _getMillisec();
    if (updated == 0) {
        return currentU;
    }
    IUINT32 _ts_flush = nextFlushTs;
    if (_itimediff(currentU, _ts_flush) >= 0 ||
        _itimediff(currentU, _ts_flush) < -10000) {
        return currentU;
    }

    IUINT32 tmin = _ts_flush; //_ts_flush>currentU is guaranteed
    //calculate most near rto
    // for (auto p = intBuf.begin(); p != intBuf.end(); p++) {
    //     if (_itimediff((*p)->resendts*1000, currentU)<=0) {
    //         return currentU;
    //     }
    //     tmin = _imin_(tmin,(*p)->resendts*1000);
    // }

    tmin = _imin_(tmin,currentU+INTCP_UPDATE_INTERVAL);
    return tmin;
}

//rate limitation on sending data
IUINT16 IntcpTransCB::getSendRate(){
    float rate;
    if(hopSrtt==0){    //haven't receive feedback
        rate = INTCP_SENDRATE_MIN;
    }else{
        // suppose rcvBuf and rcvQueue is always big enough
        rate = bytesToMbit(cwnd*INTCP_MSS)/hopSrtt*1000; //Mbps
        if(nodeRole != INTCP_REQUESTER){ // MIDNODE
            float rateForQueue = bytesToMbit(INTCP_SNDQ_MAX-sndQueueBytes)/hopSrtt*1000+rmtSendRate;
            LOG(TRACE,"%.2f",rateForQueue);
            rate = min(rate,rateForQueue);
        }
        rate = max(rate, INTCP_SENDRATE_MIN);
    }
    return IUINT16(rate*100);
}

//cc
void IntcpTransCB::updateCwnd(IUINT32 dataLen){
    IUINT32 current = _getMillisec();

    bool congSignal;
    int minHrtt=99999999;
    if(CCscheme == INTCP_CC_SCHM_LOSSB){
        congSignal = hasLossEvent;
        hasLossEvent = false;
    } else if(CCscheme == INTCP_CC_SCHM_RTTB){
        while(!hrttQueue.empty() 
                && current - hrttQueue.begin()->first > HrttMinWnd){
            hrttQueue.pop_front();
        }
        hrttQueue.push_back(pair<IUINT32,int>(current,hopSrtt));
        for(auto pr: hrttQueue){
            minHrtt = min(minHrtt, pr.second);
        }
        if(thrpLastHRTT == -1){
            congSignal = false;
        }else{
            congSignal = mbitToBytes(thrpLastHRTT)*(hopSrtt - minHrtt)/1000 > QueueingThreshold;
        }
    }
    IUINT32 cwndOld = cwnd;// for debug
    //LOG(SILENT,"cwnd %d mtu\n",cwnd);

    ccDataLen += dataLen;

    if(ccState==INTCP_CC_SLOW_START){
        if(congSignal || cwnd>=INTCP_SSTHRESH_INIT){ // entering ca
            ccDataLen = cwnd*INTCP_MSS;
            ccState = INTCP_CC_CONG_AVOID;
        } else {
            cwnd = (ccDataLen/INTCP_MSS)*(pow(2,min(5.0,double(hopSrtt)/INTCP_RTT0))-1);
        }
    }
    if(ccState==INTCP_CC_CONG_AVOID && allow_cwnd_decrease(current)){
        if(congSignal){
            //NOTE cwnd decrease function
            if(CCscheme == INTCP_CC_SCHM_LOSSB){
                cwnd = max(IUINT32(cwnd/2),INTCP_CWND_MIN);
            }else if(CCscheme == INTCP_CC_SCHM_RTTB){
                LOG(DEBUG,"%u thrp %.2f curHRtt %d minHRtt%d",current,thrpLastHRTT,hopSrtt,minHrtt);
                if(2*mbitToBytes(thrpLastHRTT)/1000*minHrtt/INTCP_MSS > cwnd+INTCP_CWND_MIN){
                    cwnd = mbitToBytes(thrpLastHRTT)/1000*(hopSrtt+minHrtt)/INTCP_MSS - cwnd;
                }else{
                    cwnd = INTCP_CWND_MIN;
                }
                cwnd = max(cwnd,INTCP_CWND_MIN);
            }
            lastCwndDecrTs = current;
            ccDataLen = 0;
            congSignal = false;
        }else{
            //printf("ccDataLen=%u bytes,cwnd = %u\n",ccDataLen,cwnd);
            if(ccDataLen>cwnd*INTCP_MSS){
                if(allow_cwnd_increase()){
                    cwnd += pow(float(hopSrtt)/INTCP_RTT0,2);
                }else{
                    double dec = pow(float(hopSrtt)/INTCP_RTT0,2)/10;
                    if(dec+INTCP_CWND_MIN >= cwnd){
                        cwnd = INTCP_CWND_MIN;
                    }else{
                        cwnd -= dec;
                    }
                }
                ccDataLen = 0;
            }
        }
    }
    if(cwndOld != cwnd){
        LOG(DEBUG,"cwnd %u",cwnd);
    }
}

bool IntcpTransCB::allow_cwnd_increase(){
    if(thrpLastHRTT==0||cwnd==0)
        return true;
    if(thrpLastHRTT < (bytesToMbit(cwnd*INTCP_MSS)/hopSrtt*1000)/2 )
        return false;
    return true;
}

bool IntcpTransCB::allow_cwnd_decrease(IUINT32 current){
    if(lastCwndDecrTs==0||hopSrtt==0)
        return true;
    //NOTE
    if(_itimediff(current,lastCwndDecrTs)<hopSrtt*2)
        return false;
    return true;
}


//assume that there is exactly one INTCP packet in one recvUDP()
int IntcpTransCB::judgeSegDst(const char *data, long size){
    if (data == nullptr || (int)size < (int)INTCP_OVERHEAD) return -1;
    IUINT8 cmd;
    // have to use a typecasting here, not good
    decode8u((char*)data, &cmd);
    if(cmd==INTCP_CMD_INT){
        return INTCP_RESPONDER;
    } else {
        return INTCP_REQUESTER;
    }
}


// peek data size
int IntcpTransCB::peekSize()
{

    if (rcvQueue.empty()) return -1;    //recv_queue

    return (*rcvQueue.begin())->len;
}

int IntcpTransCB::getRwnd()
{
    if (rcvQueue.size() < INTCP_WND_RCV) {
        return INTCP_WND_RCV - rcvQueue.size();
    }
    return 0;
}

int IntcpTransCB::getWaitSnd()
{
    return sndQueue.size();
}

IUINT32 IntcpTransCB::getCwnd(){
    return cwnd;
}
