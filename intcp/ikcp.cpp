#include "./include/ikcp.h"
#undef LOG_LEVEL
#define LOG_LEVEL DEBUG

//DEBUG
#include <iostream>
using namespace std;

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
snd_nxt(0),
snd_nxt_int(0),
rcv_nxt(0),
rcv_wnd(INTCP_WND_RCV), // for app recv buffer
cwnd(1),    //initialize with mtu
incr(INTCP_MSS),
state(0),
rx_srtt(0),
rx_rttval(0),
rx_rto(INTCP_RTO_DEF),
rx_minrto(INTCP_RTO_MIN),
hop_srtt(0),
hop_rttval(0),
updateInterval(INTCP_UPDATE_INTERVAL),
nextFlushTs(INTCP_UPDATE_INTERVAL),
updated(0),
ssthresh(INTCP_SSTHRESH_INIT),    //cc
xmit(0),
dead_link(INTCP_DEADLINK),
dataSnRightBound(-1),
dataByteRightBound(-1),
dataRightBoundTs(-1),
intSnRightBound(-1),
intByteRightBound(-1),
intRightBoundTs(-1),
cc_status(INTCP_CC_SLOW_START),
ca_data_len(0),
dataOutputLimit(0),
// rmt_sndq_rest(INTCP_SNDQ_INIT),
sndq_bytes(0),
intOwd(-1),
rmtPacingRate(INTCP_PCRATE_MIN),
intOutputLimit(0),
int_buf_bytes(0),
last_cwnd_decrease_ts(0),
throuput_update_ts(0),
rtt_received_bytes(0),
rtt_throughput(0),
hasLossEvent(false),
throughput(-1)
{
    ssid = _getMillisec()%10000;
    void *tmp = malloc(INTCP_MTU * 3);
    assert(tmp != NULL);
    tmpBuffer = shared_ptr<char>(static_cast<char*>(tmp));
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
    // for(list<IntcpSeg*>::iterator tmp=rcv_queue.begin(); tmp != rcv_queue.end(); tmp++) {
    //     LOG(DEBUG,"rcv_queue seg %d [%d,%d)",i++,(*tmp)->rangeStart,(*tmp)->rangeEnd);
    // }

    list<shared_ptr<IntcpSeg>>::iterator p;
    int recover = 0;
    shared_ptr<IntcpSeg> seg;

    if (rcv_queue.empty())
        return -1;
    //printf("111\n");
    if (rcv_queue.size() >= rcv_wnd)
        recover = 1;

    if(nodeRole == INTCP_MIDNODE){
        shared_ptr<IntcpSeg> firstSeg = *rcv_queue.begin();
        if(firstSeg->len <= maxBufSize){
            *startPtr = firstSeg->rangeStart;
            *endPtr = firstSeg->rangeEnd;
            memcpy(buffer, firstSeg->data, firstSeg->len);
            rcv_queue.pop_front();
        }
        //TODO else split
    } else {
        // copy seg->data in rcv_queue to buffer as much as possible
        *startPtr = *endPtr = (*rcv_queue.begin())->rangeStart;
        for (p = rcv_queue.begin(); p != rcv_queue.end(); ) {
            seg = *p;
            if(seg->len+ *endPtr - *startPtr > maxBufSize)
                break;
            if(*endPtr != seg->rangeStart)
                break;
            memcpy(buffer, seg->data, seg->len);
            buffer += seg->len;
            *endPtr += seg->len;
            
            rcv_queue.erase(p++);
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
        snd_queue.push_back(seg);
        sndq_bytes += seg->len;
        LOG(TRACE, "sendData sn %d [%d,%d) ",seg->sn,seg->rangeStart,seg->rangeEnd);
        buffer += size;
        len -= size;
    }

    return 0;
}


//add (rangeStart,rangeEnd) to int_queue
int IntcpTransCB::request(IUINT32 rangeStart,IUINT32 rangeEnd){
    // LOG(DEBUG,"%ld",int_buf.size());//DEBUG
    if(rangeEnd <= rangeStart){
        LOG(WARN,"rangeStart %d rangeEnd %d",rangeStart,rangeEnd);
        return -2;
    }
    if(int_buf_bytes >= INTCP_INTB_MAX){//TODO make it a parameter
        return -1;
    }
    IntRange intr;
    intr.start = rangeStart;
    intr.end = rangeEnd;
    int_queue.push_back(intr);
    return 0;
}
//---------------------------------------------------------------------
// update rtt(call when receive data)
//---------------------------------------------------------------------
void IntcpTransCB::updateRTT(IINT32 rtt)
{
    if(rtt<=0){
        return;
    }
    IINT32 rto = 0;
    if (rx_srtt == 0) {
        rx_srtt = rtt;
        rx_rttval = rtt / 2;
    }    else {
        long delta = rtt - rx_srtt;
        if (delta < 0) delta = -delta;
        rx_rttval = (3 * rx_rttval + delta) / 4;
        rx_srtt = (7 * rx_srtt + rtt) / 8;
        if (rx_srtt < 1) rx_srtt = 1;
    }
    rto = rx_srtt + _imax_(updateInterval, 4 * rx_rttval);
    rx_rto = _ibound_(rx_minrto, rto, INTCP_RTO_MAX);

}

void IntcpTransCB::updateHopRtt(IINT32 hop_rtt){
    if(hop_srtt ==0){
        hop_srtt = hop_rtt;
        hop_rttval = hop_rtt/2; 
    }
    else{
        long delta = hop_rtt - hop_srtt;
        if (delta < 0) delta = -delta;
        hop_rttval = (3 * hop_rttval + delta) / 4;
        hop_srtt = (7 * hop_srtt + hop_rtt) / 8;
        if (hop_srtt < 1) hop_srtt = 1;
    }
}

void IntcpTransCB::detectIntHole(IUINT32 rangeStart, IUINT32 rangeEnd, IUINT32 sn){
    // if(isMidnode){
    if(true){
        IUINT32 current = _getMillisec();
        if(intSnRightBound==-1 || current-intRightBoundTs>INTCP_SEQHOLE_TIMEOUT){
            intSnRightBound = sn+1;
            intByteRightBound = rangeEnd;
            intRightBoundTs = current;
            intHoles.clear();
        }else{
            // locate the position of seg in intHoles
            list<Hole>::iterator iter,next;
            for(iter=intHoles.begin(); iter!=intHoles.end();iter=next){
                next=iter;next++;
                if(current-iter->ts>INTCP_SEQHOLE_TIMEOUT){
                    intHoles.erase(iter);
                } else if(sn >= iter->end){
                    iter->count++;
                    if(iter->count >= INTCP_SEQHOLE_THRESHOLD){
                        if(iter->byteEnd - iter->byteStart > (iter->end - iter->start)*INTCP_INT_RANGE_LIMIT){
                            LOG(DEBUG, "abnormal! ignore this hole");
                        } else {
                            LOG(DEBUG,"---- int hole [%d,%d) cur %u----", iter->byteStart, iter->byteEnd, current);
                            parseInt(iter->byteStart, iter->byteEnd);
                        }
                        intHoles.erase(iter);
                    }
                } else if(sn >= iter->start){
                    if(sn == iter->start){
                        if(sn == iter->end-1){ // hole is fixed
                            intHoles.erase(iter);
                        } else {
                            iter->start++;
                            iter->byteStart = rangeEnd;
                        }
                    }else if(sn == iter->end-1){
                        iter->end--;
                        iter->byteEnd = rangeStart;
                        iter->count++;
                    }else{
                        Hole newHole;
                        newHole.count = iter->count;
                        newHole.start = sn+1;
                        newHole.end = iter->end;
                        newHole.byteStart = rangeEnd;
                        newHole.byteEnd = iter->byteEnd;
                        newHole.ts = iter->ts;
                        intHoles.insert(next, newHole);

                        iter->end = sn;
                        iter->byteEnd = rangeStart;
                        iter->count++;
                    }
                } else { // segPtr->sn < iter->start
                    // for this hole and subsequent holes, all hole.start > sn
                    break;
                }
            }
            if(sn >= intSnRightBound){
                if(sn > intSnRightBound && (rangeStart>intByteRightBound)){
                    // add a new hole
                    Hole newHole;
                    newHole.start = intSnRightBound;
                    newHole.end = sn;
                    newHole.byteStart = intByteRightBound;
                    newHole.byteEnd = rangeStart;
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
                snprintf(tmp,100,"   [ st %d end %d bSt %d bEnd %d ]",ho.start,ho.end,ho.byteStart,ho.byteEnd);
                str += tmp;
            }
            LOG(TRACE,"sn %d intHoles: %ld %s",
                    sn,intHoles.size(),str.c_str());
        }
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
            // push fetched data(less than mtu) to snd_queue
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
            // append interest to recvedInts
            if(rangeEnd <= rangeStart){
                LOG(WARN,"rangeStart %d rangeEnd %d",rangeStart,rangeEnd);
                return;
            }
            IntRange ir;
            ir.ts = _getMillisec();
            ir.start = sentEnd;
            ir.end = rangeEnd;
            recvedInts.push_back(ir);
            LOG(TRACE,"unsat [%d,%d)",sentEnd,rangeEnd);
            onUnsatInt(sentEnd, rangeEnd, user);
        }else if(nodeRole==INTCP_REQUESTER){
            //TODO should be pushed to int_queue for shaping?

            // plan A
            // shared_ptr<IntcpSeg> newseg = createSeg(0);
            // newseg->len = 0;
            // newseg->cmd = INTCP_CMD_INT;
            // newseg->xmit = 0;
            // newseg->ts = ts;
            // newseg->rangeStart = sentEnd;
            // newseg->rangeEnd = rangeEnd;
            // int_buf.push_back(newseg); 

            // plan B
            // request(sentEnd, rangeEnd);

            // plan C
            // neither pushed to int_queue nor to int_buf, send it directly
            shared_ptr<IntcpSeg> segPtr = createSeg(0);
            segPtr->len = 0;
            segPtr->cmd = INTCP_CMD_INT;
            segPtr->rangeStart = sentEnd;
            segPtr->rangeEnd = rangeEnd;
            segPtr->ts = _getMillisec();
            segPtr->wnd = getPacingRate();
            segPtr->sn = snd_nxt_int++;
            encodeSeg(tmpBuffer.get(), segPtr.get());
            output(tmpBuffer.get(), INTCP_OVERHEAD, INTCP_RESPONDER);
            // rmt_sndq_rest -= segPtr->rangeEnd - segPtr->rangeStart;
        } else { //INTCP_MIDNODE
            request(sentEnd, rangeEnd);
        }
    }
}

void IntcpTransCB::notifyNewData(const char *buffer, IUINT32 dataStart, IUINT32 dataEnd){
    if(recvedInts.empty())
        return;
    list<IntRange>::iterator p, next;
    IntcpSeg* seg;
    for (p = recvedInts.begin(); p != recvedInts.end(); p = next) {
        next = p; next++;
        int intStart = p->start, intEnd = p->end, ts = p->ts;
        // check if the union is not empty
        if (_itimediff(intStart,dataEnd) <0 && _itimediff(intEnd,dataStart) >0){
            IUINT32 maxStart = _imax_(intStart, dataStart);
            IUINT32 minEnd = _imin_(intEnd, dataEnd);
            LOG(TRACE,"satisfy pending int: [%d,%d)",maxStart,minEnd);
            sendData(buffer+maxStart-dataStart, maxStart, minEnd);
            if(maxStart==intStart && minEnd==intEnd) {
                recvedInts.erase(p);
            } else if (minEnd==intEnd) {
                // partly sent
                p->end = maxStart;
            } else {
                p->start = minEnd;
                if (maxStart!=intStart) {
                    IntRange ir;
                    ir.ts = ts;
                    ir.start = intStart;
                    ir.end = maxStart;
                    recvedInts.insert(p,ir);
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
    if(dataSnRightBound==-1 || current-dataRightBoundTs>INTCP_SEQHOLE_TIMEOUT){
        dataSnRightBound = sn+1;
        dataByteRightBound = rangeEnd;
        dataRightBoundTs = current;
        dataHoles.clear();
    }else{
        // locate the position of seg in dataHoles
        list<Hole>::iterator iter,next;
        for(iter=dataHoles.begin(); iter!=dataHoles.end();iter=next){
            next=iter;next++;
            if(current-iter->ts>INTCP_SEQHOLE_TIMEOUT){
                dataHoles.erase(iter);
            } else if(sn >= iter->end){
                iter->count++;
                if(iter->count >= INTCP_SEQHOLE_THRESHOLD){
                    found_new_loss = true;
                    if(iter->byteEnd - iter->byteStart > (iter->end - iter->start)*INTCP_MSS){
                        LOG(DEBUG, "abnormal hole! [%d,%d) sn [%d,%d)",
                                iter->byteStart, iter->byteEnd,iter->start,iter->end);
                        // for(auto kh:dataHoles){
                        //     cout<<kh.byteStart<<','<<kh.byteEnd<<' ';
                        // }
                        // cout<<endl;
                    } else {
                        LOG(TRACE,"---- d hole [%u,%u) [%u,%u) t %u----", iter->start,iter->end,iter->byteStart, iter->byteEnd, current);
                        parseInt(iter->byteStart,iter->byteEnd);
                        list<shared_ptr<IntcpSeg>>::iterator iterInt;
                        // if the range of this hole could cover an interest in int_buf, modify the resendts of interest
                        for(iterInt=int_buf.begin();iterInt!=int_buf.end();iterInt++){
                            if(max(iter->byteStart,(*iterInt)->rangeStart) < min(iter->byteEnd,(*iterInt)->rangeEnd)){
                                //------------------------------
                                // update int_buf
                                //------------------------------
                                if(iter->byteStart <= (*iterInt)->rangeStart){
                                    if(iter->byteEnd >= (*iterInt)->rangeEnd){    //range completely received
                                        (*iterInt)->ts = _getMillisec();
                                        (*iterInt)->resendts = (*iterInt)->ts + (*iterInt)->rto;
                                    }else{
                                        shared_ptr<IntcpSeg> newseg = createSeg(0);
                                        memcpy(newseg.get(), (*iterInt).get(), sizeof(IntcpSeg));
                                        newseg->rangeStart = iter->byteEnd;
                                        (*iterInt)->rangeEnd = iter->byteEnd;
                                        (*iterInt)->ts = _getMillisec();
                                        (*iterInt)->resendts = (*iterInt)->ts + (*iterInt)->rto;

                                        int_buf.insert(iterInt,newseg);
                                        iterInt++;
                                    }
                                } else if(iter->byteEnd >= (*iterInt)->rangeEnd){
                                    shared_ptr<IntcpSeg> newseg = createSeg(0);
                                    memcpy(newseg.get(), (*iterInt).get(), sizeof(IntcpSeg));
                                    newseg->rangeStart = iter->byteStart;
                                    (*iterInt)->rangeEnd = iter->byteStart;
                                    newseg->ts = _getMillisec();
                                    newseg->resendts = newseg->ts + newseg->rto;
                                    int_buf.insert(iterInt,newseg);
                                    iterInt++;
                                }else{
                                    shared_ptr<IntcpSeg> newseg = createSeg(0);
                                    memcpy(newseg.get(), (*iterInt).get(), sizeof(IntcpSeg));
                                    newseg->rangeStart = iter->byteEnd;
                                    int_buf.insert(iterInt,newseg);

                                    newseg = createSeg(0);
                                    memcpy(newseg.get(), (*iterInt).get(), sizeof(IntcpSeg));
                                    newseg->rangeStart = iter->byteStart;
                                    newseg->rangeEnd = iter->byteEnd;
                                    newseg->ts = _getMillisec();
                                    newseg->resendts = newseg->ts + newseg->rto;
                                    int_buf.insert(iterInt,newseg);

                                    (*iterInt)->rangeEnd = iter->byteStart;
                                    iterInt++;
                                    iterInt++;
                                }
                            }
                        }
                    }
                    dataHoles.erase(iter);
                }
            } else if(sn >= iter->start){
                if(sn == iter->start){
                    if(sn == iter->end-1){ // hole is fixed
                        dataHoles.erase(iter);
                    } else {
                        iter->start++;
                        iter->byteStart = rangeEnd;
                    }
                }else if(sn == iter->end-1){
                    iter->end--;
                    iter->byteEnd = rangeStart;
                    iter->count++;
                }else{
                    Hole newHole;
                    newHole.count = iter->count;
                    newHole.start = sn+1;
                    newHole.end = iter->end;
                    newHole.byteStart = rangeEnd;
                    newHole.byteEnd = iter->byteEnd;
                    newHole.ts = iter->ts;
                    dataHoles.insert(next, newHole);

                    iter->end = sn;
                    iter->byteEnd = rangeStart;
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
                newHole.start = dataSnRightBound;
                newHole.end = sn;
                newHole.byteStart = dataByteRightBound;
                newHole.byteEnd = rangeStart;
                LOG(TRACE,"---- data hole [%d,%d) cur %u----", newHole.byteStart, newHole.byteEnd, current);
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
            snprintf(tmp,100,"   [ st %d end %d bSt %d bEnd %d ]",ho.start,ho.end,ho.byteStart,ho.byteEnd);
            str += tmp;
        }
        LOG(TRACE,"sn %d dataHoles: %ld %s",
                sn,dataHoles.size(),str.c_str());
    }
    return found_new_loss;
}



void IntcpTransCB::parseData(shared_ptr<IntcpSeg> segPtr)
{
    if(nodeRole == INTCP_REQUESTER){
        list<shared_ptr<IntcpSeg>>::iterator intIter, intNext;
        //in requester, need to delete range of int_buf
        for (intIter = int_buf.begin(); intIter != int_buf.end(); intIter = intNext) {
            shared_ptr<IntcpSeg> intSeg = *intIter;
            intNext = intIter; intNext++;
            // if (_itimediff(sn, intSeg->rangeStart) < 0){
            //     break;
            // }
            if (segPtr->rangeStart < intSeg->rangeEnd && segPtr->rangeEnd > intSeg->rangeStart) {
                LOG(TRACE,"[%d,%d) rtt %d current %u xmit %d",segPtr->rangeStart,segPtr->rangeEnd,
                        _getMillisec()-intSeg->ts, _getMillisec(), intSeg->xmit);
                updateRTT(_itimediff(_getMillisec(), intSeg->ts));
                //-------------------------------
                // insert [the intersection of seg and interest] into rcv_buf
                //-------------------------------
                int intsecStart = _imax_(intSeg->rangeStart,segPtr->rangeStart);
                int intsecEnd = _imin_(intSeg->rangeEnd,segPtr->rangeEnd);
                shared_ptr<IntcpSeg> intsecDataSeg = createSeg(intsecEnd-intsecStart);
                intsecDataSeg->rangeStart = intsecStart;
                intsecDataSeg->rangeEnd = intsecEnd;
                intsecDataSeg->len = intsecEnd-intsecStart;
                memcpy(intsecDataSeg->data, segPtr->data+intsecStart-segPtr->rangeStart,
                        intsecEnd-intsecStart);
                //DEBUG
                IUINT32 cur_tmp = _getMillisec();
                // LOG(DEBUG,"xmit %u rto %u rcvTime %u",intSeg->xmit,intSeg->rto,cur_tmp);
                memcpy(intsecDataSeg->data+sizeof(IUINT32), &intSeg->xmit, sizeof(IUINT32));
                memcpy(intsecDataSeg->data+sizeof(IUINT32)*2, &cur_tmp, sizeof(IUINT32));
                // memcpy(intsecDataSeg->data+sizeof(IUINT32)*3, &intSeg->firstTs, sizeof(IUINT32));
                
                if(rcv_buf.empty()){
                    rcv_buf.push_back(intsecDataSeg);
                }else{
                    int found=0;
                    list<shared_ptr<IntcpSeg>>::iterator dataIter;
                    for (dataIter = rcv_buf.end(); dataIter != rcv_buf.begin(); ) {
                        --dataIter;
                        shared_ptr<IntcpSeg> iterSeg = *dataIter;
                        if (_itimediff(intsecDataSeg->rangeStart, iterSeg->rangeEnd) >= 0) {
                            found = 1;
                            break;
                        }
                    }
                    if(found==1){
                        rcv_buf.insert(++dataIter,intsecDataSeg);
                    }else{
                        rcv_buf.insert(dataIter,intsecDataSeg);
                    }
                }

                //------------------------------
                // update int_buf
                //------------------------------
                int_buf_bytes -= intsecEnd - intsecStart;
                if(segPtr->rangeStart <= intSeg->rangeStart){
                    if(segPtr->rangeEnd >= intSeg->rangeEnd){    //range completely received
                        int_buf.erase(intIter);
                    }
                    else{
                        intSeg->rangeStart = segPtr->rangeEnd;
                    }
                } else if(segPtr->rangeEnd >= intSeg->rangeEnd){
                    intSeg->rangeEnd = segPtr->rangeStart;
                }else{
                    //intSeg->rangeEnd = sn;
                    shared_ptr<IntcpSeg> newseg = createSeg(0);
                    memcpy(newseg.get(), intSeg.get(), sizeof(IntcpSeg));
                    intSeg->rangeEnd = segPtr->rangeStart;
                    newseg->rangeStart = segPtr->rangeEnd;
                    
                    int_buf.insert(intIter,newseg);
                }
            }
        }
    } else {
        shared_ptr<IntcpSeg> segToForward = createSeg(segPtr->len);
        //TODO copy char[] pointer??
        memcpy(segToForward.get(),segPtr.get(),INTCP_OVERHEAD+segPtr->len);
        snd_queue.push_back(segToForward);
        sndq_bytes += segToForward->len;
        // receiving by upper layer delete this seg, 
        // output also delete it, so we need two seg
        // in sendData(), the sn will be rewrite
        // sendData(data, rangeStart, rangeEnd);
        rcv_buf.push_back(segPtr);
    }

    moveToRcvQueue();
}

//reordering in requester: queueing in order of interest
// (suppose interest is in order now)
// move available data from rcv_buf -> rcv_queue
void IntcpTransCB::moveToRcvQueue(){
    
    while (!rcv_buf.empty()) {
        if(nodeRole == INTCP_MIDNODE){
            // LOG(DEBUG,"rq size %ld rw %u",rcv_queue.size(), rcv_wnd);
            if(rcv_queue.size() < rcv_wnd){
                rcv_queue.splice(rcv_queue.end(),rcv_buf,rcv_buf.begin(),rcv_buf.end());
            }else{
                break;
            }
        }else{
            shared_ptr<IntcpSeg> seg = *rcv_buf.begin();
            if (seg->rangeStart == rcv_nxt && rcv_queue.size() < rcv_wnd) {
                rcv_nxt = seg->rangeEnd;
                rcv_queue.splice(rcv_queue.end(),rcv_buf,rcv_buf.begin());
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
            intOwd = _getMillisec() - ts;
            rmtPacingRate = wnd;
            LOG(TRACE, "recv int [%d,%d)",rangeStart,rangeEnd);
            detectIntHole(rangeStart,rangeEnd,sn);
            parseInt(rangeStart,rangeEnd);
        } else if (cmd == INTCP_CMD_PUSH) {
            LOG(TRACE, "input data sn %d [%d,%d)", sn, rangeStart,rangeEnd);

            //TODO avoid memcpy
            // if (isMidnode) {
            //     decode16u(dataOrg+sizeof(cmd),&wnd);
            //     outputFunc(dataOrg, sizeOrg, user, INTCP_REQUESTER);
            // }

            if(true){
                // rmt_sndq_rest = wnd*INTCP_MSS;//TODO for midnode, ignore this part
                // LOG(TRACE,"%d",rmt_sndq_rest);
                if(_getMillisec()>ts){
                    updateHopRtt(_getMillisec()-ts);
                }else{
                    LOG(WARN,"_getMillisec()>ts");
                }
                if(detectDataHole(rangeStart,rangeEnd,sn)){
                    hasLossEvent = true;
                }
                updateCwnd(len);
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
            }
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
    while(!int_queue.empty()){
        shared_ptr<IntcpSeg> newseg = createSeg(0);
        assert(newseg);
        newseg->len = 0;
        newseg->sn = 0;
        newseg->cmd = INTCP_CMD_INT;
        
        // resendts and rto will be set before output
        newseg->xmit = 0;
        
        bool first = true;
        //NOTE assume that rangeEnd of interest in int_queue is in order
        for(list<IntRange>::iterator iter=int_queue.begin();iter!=int_queue.end();){
            if(first){
                newseg->rangeStart = iter->start;
                newseg->rangeEnd = _imin_(iter->end, newseg->rangeStart+INTCP_INT_RANGE_LIMIT);
                first = false;
            } else {
                if(iter->start == newseg->rangeEnd){
                    LOG(TRACE,"%u %u %u %u",newseg->rangeStart,newseg->rangeEnd,iter->start,iter->end);
                    // newseg->rangeStart = _imin_(iter->start,newseg->rangeStart);
                    newseg->rangeEnd = _imin_(iter->end,
                            newseg->rangeStart+INTCP_INT_RANGE_LIMIT);
                } else {
                    break;
                }
            }
            if(iter->end <= newseg->rangeEnd){
                int_queue.erase(iter++);
            } else {
                iter->start = newseg->rangeEnd;
                break;
            }
        }
        // intRangeLimit -= newseg->rangeEnd-newseg->rangeStart;
        int_buf_bytes += newseg->rangeEnd-newseg->rangeStart;
        int_buf.push_back(newseg);
    }
}

void IntcpTransCB::flushIntBuf(){
    // if(nodeRole==INTCP_REQUESTER && rmt_sndq_rest<= 0){
    //     return;
    // }
    // intOutputLimit += int(float(rmt_sndq_rest)/rx_srtt*INTCP_UPDATE_INTERVAL/1000);
    //TODO CC
    char *sendEnd=tmpBuffer.get();
    int sizeToSend=0;
    // from int_buf to udp
    list<shared_ptr<IntcpSeg>>::iterator p,next;
    //DEBUG
    int cnt=0,cntRTO=0,cntXmit=0;
    bool reach_limit = false;
    for (p = int_buf.begin(); p != int_buf.end(); p=next) {
        cnt++;
        next=p;next++;
        IUINT32 current = _getMillisec();
        //TODO write segPtr->ts here??
        shared_ptr<IntcpSeg> segPtr = *p;
        int needsend = 0;
        if(nodeRole == INTCP_MIDNODE){
            needsend = 1;
        } else {
            // RTO mechanism
            if (segPtr->xmit >= 2) {cntXmit++;}
            if (segPtr->xmit == 0) {
                needsend = 1;
                segPtr->rto = IUINT32(rx_rto*INTCP_RTO_FACTOR);
                // segPtr->resendts = current + segPtr->rto + rx_rto >> 3;
                LOG(TRACE,"request [%d,%d) rto %d",segPtr->rangeStart,segPtr->rangeEnd, IUINT32(segPtr->rto*INTCP_RTO_FACTOR));
                segPtr->resendts = current + segPtr->rto;// + rx_rto >> 3;
            } else if (_itimediff(current, segPtr->resendts) >= 0) {
                hasLossEvent = true;
                cntRTO++;
                LOG(TRACE,"----- Timeout [%d,%d) xmit %d cur %u rto %d -----",
                        segPtr->rangeStart, segPtr->rangeEnd, segPtr->xmit, _getMillisec(),segPtr->rto);
                needsend = 1; //1 -> 0
                xmit++;//TODO if sndq limit occurs, withdraw
                segPtr->rto += _imax_(segPtr->rto, (IUINT32)rx_rto);
                segPtr->resendts = current + segPtr->rto;
            }
        }

        if (needsend) {
            //clear hole
            if(nodeRole != INTCP_MIDNODE){
                list<Hole>::iterator iter,next;
                for(iter=dataHoles.begin(); iter!=dataHoles.end();iter=next){
                    next=iter;next++;
                    IUINT32 maxStart = _imax_(segPtr->rangeStart,iter->byteStart);
                    IUINT32 minEnd = _imin_(segPtr->rangeEnd, iter->byteEnd);
                    if(maxStart < minEnd){
                        LOG(TRACE, "RTO[%d,%d) cover hole [%d,%d)", segPtr->rangeStart, segPtr->rangeEnd, iter->byteStart, iter->byteEnd);
                        if(maxStart == iter->byteStart){
                            if(minEnd == iter->byteEnd){ // hole is fixed
                                dataHoles.erase(iter);
                            } else {
                                iter->byteStart = minEnd;
                            }
                        }else if(minEnd == iter->byteEnd){
                            iter->byteEnd = maxStart;
                        }else{
                            Hole newHole;
                            newHole.count = iter->count;
                            newHole.start = iter->start;
                            newHole.end = iter->end;
                            newHole.byteStart = minEnd;
                            newHole.byteEnd = iter->byteEnd;
                            newHole.ts = iter->ts;
                            dataHoles.insert(next, newHole);

                            iter->byteEnd = maxStart;
                        }
                    }
                }
            }
            // if(nodeRole==INTCP_REQUESTER){
            //     // rmt_sndq_rest -= segPtr->rangeEnd - segPtr->rangeStart;
            //     if(intOutputLimit<segPtr->len){
            //         LOG(TRACE,"intOutputLimit %d bytes seglen %d qsize %ld",intOutputLimit,segPtr->len,snd_queue.size());
            
            //         reach_limit = true;
            //         break;
            //     }else{
            //         intOutputLimit -= segPtr->rangeEnd - segPtr->rangeStart;
            //     }
            // }
            segPtr->ts = current;
            segPtr->wnd = getPacingRate();

            segPtr->xmit++;
            segPtr->sn = snd_nxt_int++;
            sizeToSend = (int)(sendEnd - tmpBuffer.get());
            if (sizeToSend + INTCP_OVERHEAD > INTCP_MTU) {
                output(tmpBuffer.get(), sizeToSend, INTCP_RESPONDER);
                sendEnd = tmpBuffer.get();
            }
            sendEnd = encodeSeg(sendEnd, segPtr.get());
            if (segPtr->xmit >= dead_link) {
                state = (IUINT32)-1;
                LOG(ERROR, "dead link");
                abort();
            }

            if(nodeRole == INTCP_MIDNODE){
                int_buf_bytes -= (*p)->rangeEnd - (*p)->rangeStart;
                int_buf.erase(p);
            }
            // if(nodeRole==INTCP_REQUESTER && rmt_sndq_rest<= 0){
            //     break;
            // }
        }
    }
    // if(!reach_limit){
    //     intOutputLimit = 0;//min();
    // }
    LOG(TRACE,"RTO %d %d/%d/%d",rx_rto,cntRTO,cntXmit,cnt);

    // flush remain segments
    sizeToSend = (int)(sendEnd - tmpBuffer.get());
    if (sizeToSend > 0) {
        output(tmpBuffer.get(), sizeToSend, INTCP_RESPONDER);
    }
}

// snd_queue -> send straightforward;
void IntcpTransCB::flushData(){
    //TODO CC -- cwnd/sendingRate; design token bucket
    dataOutputLimit += int(float(rmtPacingRate)*1024*INTCP_UPDATE_INTERVAL/1000/1000);
    LOG(TRACE,"dataOutputLimit %d bytes %ld",dataOutputLimit,snd_queue.size());
    //int dataOutputLimit = 65536;

    char *sendEnd=tmpBuffer.get();
    int sizeToSend=0;

    bool reach_limit = false;
    list<shared_ptr<IntcpSeg>>::iterator p, next;
    shared_ptr<IntcpSeg> segPtr;
    for (p = snd_queue.begin(); p != snd_queue.end(); p=next){
        next = p; next++;
        segPtr = *p;
        if(dataOutputLimit<segPtr->len){
            LOG(TRACE,"dataOutputLimit %d bytes seglen %d qsize %ld",dataOutputLimit,segPtr->len,snd_queue.size());
    
            reach_limit = true;
            break;
        }else{
            dataOutputLimit -= segPtr->len;
        }

        sizeToSend = (int)(sendEnd - tmpBuffer.get());
        if (sizeToSend + (INTCP_OVERHEAD + segPtr->len) > INTCP_MTU) {
            output(tmpBuffer.get(), sizeToSend, INTCP_REQUESTER);
            sendEnd = tmpBuffer.get();
        }

        segPtr->sn = snd_nxt++;
        LOG(TRACE,"sn %d [%d,%d) cur %u",segPtr->sn,segPtr->rangeStart,segPtr->rangeEnd,_getMillisec());
        segPtr->ts = _getMillisec() - intOwd;
        if(nodeRole==INTCP_RESPONDER){//TODO if it's from cache, wnd=0
            segPtr->wnd = IUINT16((INTCP_SNDQ_MAX - _imin_(INTCP_SNDQ_MAX,sndq_bytes))/INTCP_MSS);
            LOG(TRACE,"%d %u",sndq_bytes,segPtr->wnd);
        }
        sendEnd = encodeSeg(sendEnd, segPtr.get());
        memcpy(sendEnd, segPtr->data, segPtr->len);
        sendEnd += segPtr->len;
        sndq_bytes -= segPtr->len;
        snd_queue.erase(p);
    }
    //if cwnd is not enough for data, the remain wnd can be used for next loop
    if(!reach_limit){
        dataOutputLimit = 0;//min();
    }
        
    // if(cwnd!=0) {
    //     LOG(DEBUG,"%d %d",rmt_cwnd,reach_limit);
    // }
    // flush remain segments
    sizeToSend = (int)(sendEnd - tmpBuffer.get());
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
    //DEBUG
    static IUINT32 printTime = _getMillisec()-1000;
    if(_getMillisec()-printTime>1000){
        if(nodeRole!=INTCP_REQUESTER){
            LOG(DEBUG,"%d| %u pcrate %d sndq %ld",
                    ssid, _getMillisec(), rmtPacingRate, snd_queue.size());
        }
        if(nodeRole!=INTCP_RESPONDER){
            LOG(TRACE,"%.3f: hrtt %d rtt %d intB_bytes %d rcvB %ld rnxt %u",
                    double(_getMillisec())/1000,hop_srtt,rx_srtt,int_buf_bytes,rcv_buf.size(),rcv_nxt);
        }
        printTime = _getMillisec();
    }
    IUINT32 current = _getUsec();
    if (updated == 0) {
        updated = 1;
        nextFlushTs = current;
    }

    IINT32 slap = _itimediff(current, nextFlushTs);

    if (slap>0 || slap<-10000000){
        // LOG(DEBUG,"iq %ld ib %ld pit %ld sq %ld rb %ld rq %ld",
        //         int_queue.size(), int_buf.size(),recvedInts.size(),
        //         snd_queue.size(),rcv_buf.size(),rcv_queue.size());
        flush();
        if (slap >= updateInterval || slap < -10000000) {
            nextFlushTs = current + updateInterval;
        } else {
            nextFlushTs = nextFlushTs + updateInterval;
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
    IUINT32 currentU = _getUsec();
    if (updated == 0) {
        return currentU;
    }
    IUINT32 _ts_flush = nextFlushTs;
    if (_itimediff(currentU, _ts_flush) >= 0 ||
        _itimediff(currentU, _ts_flush) < -10000000) {
        return currentU;
    }

    IUINT32 tmin = _ts_flush; //_ts_flush>currentU is guaranteed
    //calculate most near rto
    // for (auto p = int_buf.begin(); p != int_buf.end(); p++) {
    //     if (_itimediff((*p)->resendts*1000, currentU)<=0) {
    //         return currentU;
    //     }
    //     tmin = _imin_(tmin,(*p)->resendts*1000);
    // }

    tmin = _imin_(tmin,currentU+INTCP_UPDATE_INTERVAL);
    return tmin;
}


int IntcpTransCB::getRwnd()
{
    if (rcv_queue.size() < rcv_wnd) {
        return rcv_wnd - rcv_queue.size();
    }
    return 0;
}

int IntcpTransCB::getWaitSnd()
{
    return snd_queue.size();
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

    if (rcv_queue.empty()) return -1;    //recv_queue

    return (*rcv_queue.begin())->len;
}

//rate limitation on sending data
IUINT16 IntcpTransCB::getPacingRate(){
    if(hop_srtt==0||cwnd==0){    //haven't receive feedback
        // LOGL(DEBUG);
        return INTCP_PCRATE_MIN;
    }else{
        IUINT32 swnd;
        if(nodeRole == INTCP_REQUESTER){
            swnd = cwnd; // suppose rcv_buf and rcv_queue is always big enough
        } else {
            swnd = min(cwnd,(INTCP_SNDQ_MAX-sndq_bytes)/INTCP_MSS);
        }
        IUINT16 rate = float(swnd*INTCP_MSS)/hop_srtt*1000/1024;
        // LOG(DEBUG, "%u %u",cwnd,rate);
        if(rate<INTCP_PCRATE_MIN){
            rate = INTCP_PCRATE_MIN;
        }
        return rate;
    }
}

//cc
void IntcpTransCB::updateCwnd(IUINT32 dataLen){
    IUINT32 current = _getMillisec();
    bool congSignal;
    if(CCscheme == INTCP_CC_LOSSB){
        congSignal = hasLossEvent;
        hasLossEvent = false;
    } else if(CCscheme == INTCP_CC_RTTB){
        while(!hrtt_queue.empty() 
                && current - hrtt_queue.begin()->first > HrttMinWnd){
            hrtt_queue.pop_front();
        }
        hrtt_queue.push_back(pair<IUINT32,int>(current,hop_srtt));
        int minHrtt=99999999;
        for(auto pr: hrtt_queue){
            minHrtt = min(minHrtt, pr.second);
        }
        if(throughput == -1){
            congSignal = false;
        }else{
            congSignal = throughput*(hop_srtt - minHrtt) > QueueingThreshold;
            if(congSignal)
                LOG(TRACE,"%f %d %d",throughput,hop_srtt,minHrtt);
        }
    }
    IUINT32 cwndOld = cwnd;//DEBUG
    //LOG(SILENT,"cwnd %d mtu\n",cwnd);
    
    
    if(hop_srtt!=0){ //only begin calculate throughput when hoprtt exists
        if(throuput_update_ts==0)
            throuput_update_ts= current;
        if(_itimediff(current,throuput_update_ts)>hop_srtt){
            rtt_throughput = rtt_received_bytes;
            throughput = float(rtt_received_bytes)/hop_srtt;
            LOG(TRACE,"receive rate = %.2fMbps",8*((float)rtt_throughput)/(hop_srtt*1024));
            rtt_received_bytes = 0;
            throuput_update_ts = current;
        }
        // if(!found_new_loss)
        rtt_received_bytes+=dataLen;
    }
    
    if(cc_status==INTCP_CC_SLOW_START){      //slow start
        if(congSignal){                //??
            cwnd = cwnd/2;
            if(cwnd<1)
                cwnd=1;
            ssthresh = max(cwnd,INTCP_SSTHRESH_MIN);
            incr = cwnd*INTCP_MSS;
            last_cwnd_decrease_ts = current;
            cc_status == INTCP_CC_CONG_AVOID;
        }
        else{
            incr += dataLen;        //window expand 1mss when receive 1mss data
            cwnd = incr/INTCP_MSS;
            if(cwnd>=ssthresh){     //entering ca
                ssthresh = cwnd;
                cc_status = INTCP_CC_CONG_AVOID;
            }
        }
    }
    else if(cc_status==INTCP_CC_CONG_AVOID){
        if(congSignal){
            if(allow_cwnd_decrease(current)){
                if(CCscheme == INTCP_CC_LOSSB){
                    ssthresh = max(IUINT32(ssthresh/2),INTCP_SSTHRESH_MIN);
                }else if(CCscheme == INTCP_CC_RTTB){
                    ssthresh = max(IUINT32(ssthresh>=20?ssthresh-20:0),INTCP_SSTHRESH_MIN);
                }
                cwnd = ssthresh;
                last_cwnd_decrease_ts = current;
                ca_data_len = 0;
            }        
        }else{
            ca_data_len += dataLen;
            //printf("ca_data_len=%u bytes,cwnd = %u\n",ca_data_len,cwnd);
            if(ca_data_len>cwnd*INTCP_MSS){
                if(allow_cwnd_increase()){
                    cwnd ++;
                    ssthresh ++;
                    incr += INTCP_MSS;
                }
                ca_data_len = 0;
            }
        }
    }
    if(cwndOld != cwnd){
        LOG(TRACE,"cwnd %u %u",_getMillisec(),cwnd);
    }
}

bool IntcpTransCB::allow_cwnd_increase(){
    if(rtt_throughput==0||cwnd==0)
        return true;
    LOG(TRACE,"rtt_throughput = %u mss",rtt_throughput/INTCP_MSS);
    if(rtt_throughput<cwnd*INTCP_MSS/2)
        return false;
    return true;
}

bool IntcpTransCB::allow_cwnd_decrease(IUINT32 current){
    if(last_cwnd_decrease_ts==0||hop_srtt==0)
        return true;
    if(_itimediff(current,last_cwnd_decrease_ts)<hop_srtt)
        return false;
    return true;
}

IUINT32 IntcpTransCB::getCwnd(){
    return cwnd;
}
