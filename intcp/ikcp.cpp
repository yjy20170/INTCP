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
ts_probe(0),
probe_wait(0),
snd_wnd(INTCP_WND_SND),
rcv_wnd(INTCP_WND_RCV),
rmt_wnd(-1),             // INTCP_WND_RCV
cwnd(1),    //initialize with mtu
incr(INTCP_MTU_DEF),
probe(0),
mtu(INTCP_MTU_DEF),
mss(mtu - INTCP_OVERHEAD),
state(0),
rx_srtt(0),
rx_rttval(0),
rx_rto(INTCP_RTO_DEF),
rx_minrto(INTCP_RTO_MIN),
hop_srtt(0),
hop_rttval(0),
updateInterval(INTCP_INTERVAL),
nextFlushTs(INTCP_INTERVAL),
nodelay(0),
nocwnd(0),
updated(0),
ssthresh(INTCP_THRESH_INIT),    //cc
fastRetransThre(0),
fastRetransCountLimit(INTCP_FASTACK_LIMIT),
xmit(0),
dead_link(INTCP_DEADLINK),
dataSnRightBound(-1),
dataByteRightBound(-1),
dataRightBoundTs(-1),
intSnRightBound(-1),
intByteRightBound(-1),
intRightBoundTs(-1),
ts_hop_rtt_probe(0),
hop_rtt_probe_wait(INTCP_HOP_RTT_PROBE_INIT),
rmt_hop_rtt(0),
rmt_cwnd(0)
{
    void *tmp = malloc((mtu + INTCP_OVERHEAD) * 3);
    assert(tmp != NULL);
    tmpBuffer = shared_ptr<char>(static_cast<char*>(tmp));
}


//---------------------------------------------------------------------
// encodeSeg
//---------------------------------------------------------------------
char* IntcpTransCB::encodeSeg(char *ptr, const IntcpSeg *seg)
{
    ptr = encode8u(ptr, (IUINT8)seg->cmd);
    ptr = encode16u(ptr, (IUINT16)seg->wnd);
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

    // fast recover
    if (rcv_queue.size() < rcv_wnd && recover) {
        // ready to send back INTCP_CMD_WINS in flush
        // tell remote my window size
        probe |= INTCP_ASK_TELL;
    }

    return 0;
}

//---------------------------------------------------------------------
// user/upper level send, returns below zero for error
//---------------------------------------------------------------------
int IntcpTransCB::sendData(const char *buffer, IUINT32 start, IUINT32 end, IUINT32 tsEcho)
{
    int len = end - start;
    // if(len>64){
    //     LOG(DEBUG,"%d %d",start,end);
    // }
    shared_ptr<IntcpSeg> seg;

    assert(mss > 0);
    if (len <= 0) return -1;

    while(len>0) {
        int size = len > (int)mss ? (int)mss : len;
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
        seg->ts = tsEcho;
        start += size;
        snd_queue.push_back(seg);
		LOG(TRACE, "sendData sn %d [%d,%d) ",seg->sn,seg->rangeStart,seg->rangeEnd);
        buffer += size;
        len -= size;
    }

    return 0;
}


//add (rangeStart,rangeEnd) to int_queue
void IntcpTransCB::request(IUINT32 rangeStart,IUINT32 rangeEnd){
    if(rangeEnd <= rangeStart){
        LOG(WARN,"rangeStart %d rangeEnd %d",rangeStart,rangeEnd);
        return;
    }
    IntRange intr;
    intr.start = rangeStart;
    intr.end = rangeEnd;
    int_queue.push_back(intr);
}
//---------------------------------------------------------------------
// update rtt(call when receive data)
//---------------------------------------------------------------------
void IntcpTransCB::updateRTT(IINT32 rtt)
{
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

void IntcpTransCB::updateHopRtt(IUINT32 ts){
    // to do
    IUINT32 current = _getMillisec();
    IINT32 hop_rtt = _itimediff(current,ts);
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
    LOG(TRACE,"hop_rtt=%d,hop_srtt=%d",hop_rtt,hop_srtt);
    //printf("***hopRtt=%d\n",hop_rtt);
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
                        if(iter->byteEnd - iter->byteStart > (iter->end - iter->start)*mss){
                            LOG(DEBUG, "abnormal! ignore this hole");
                        } else {
                            LOG(DEBUG,"---- int hole [%d,%d) cur %u----", iter->byteStart, iter->byteEnd, current);
                            parseInt(iter->byteStart, iter->byteEnd, -1, -1);
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
void IntcpTransCB::parseInt(IUINT32 rangeStart, IUINT32 rangeEnd, IUINT32 ts, IUINT32 wnd){
    //TODO deal with CC info, like wnd

    IUINT32 sentEnd=rangeStart;
    if(nodeRole != INTCP_REQUESTER) {
        // first, try to fetch data
        IUINT32 segStart, segEnd;
        int fetchLen;
        for(segStart = rangeStart; segStart < rangeEnd; segStart+=mtu){
            segEnd = _imin_(rangeEnd, segStart+mtu);
            fetchLen = fetchDataFunc(tmpBuffer.get(), segStart, segEnd, user);
            sentEnd = segStart+fetchLen;
            if(fetchLen==0)
                break;
            // push fetched data(less than mtu) to snd_queue
            sendData(tmpBuffer.get(),segStart,segStart+fetchLen, ts);
            // if this seg is not completed due to data miss
            if(fetchLen<segEnd-segStart){
                break;
            }
        }
    }
    
    // rest range
    if(sentEnd<rangeEnd){
        //NOTE in midnode, if cache has [3,10], interest is [0,10], the whole cache is wasted;
        if(nodeRole == INTCP_RESPONSER){
            // append interest to recvedInts
            if(rangeEnd <= rangeStart){
                LOG(WARN,"rangeStart %d rangeEnd %d",rangeStart,rangeEnd);
                return;
            }
            IntRange ir;
            ir.ts = ts;
            ir.start = sentEnd;
            ir.end = rangeEnd;
            recvedInts.push_back(ir);
            LOG(TRACE,"unsat [%d,%d)",sentEnd,rangeEnd);
            onUnsatInt(sentEnd, rangeEnd, user);
        }else if(nodeRole == INTCP_REQUESTER){
            // requester found hole, what to do?
            // // if the range of this hole could cover an interest in int_buf, modify the resendts of interest
            // for(auto intseg:int_buf){
            //     if(intseg->rangeStart>=iter->byteStart && intseg->rangeEnd<=iter->byteEnd){
            //         LOG(TRACE, "hole[%d,%d) cover RTO[%d,%d)", iter->byteStart, iter->byteEnd,intseg->rangeStart,intseg->rangeEnd);
            //         intseg->resendts = _getMillisec() + intseg->rto;
            //     }
            // }
        }else{
            shared_ptr<IntcpSeg> newseg = createSeg(0);
            newseg->len = 0;
            newseg->cmd = INTCP_CMD_INT;
            newseg->xmit = 0;
            newseg->ts = ts;
            newseg->rangeStart = sentEnd;
            newseg->rangeEnd = rangeEnd;
            int_buf.push_back(newseg);
            // request(sentEnd, rangeEnd);
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
			sendData(buffer+maxStart-dataStart, maxStart, minEnd, ts);
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
    bool find_new_hole = false;
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
                    if(iter->byteEnd - iter->byteStart > (iter->end - iter->start)*mss){
                        LOG(DEBUG, "abnormal hole! [%d,%d) sn [%d,%d)",
                                iter->byteStart, iter->byteEnd,iter->start,iter->end);
                        // for(auto kh:dataHoles){
                        //     cout<<kh.byteStart<<','<<kh.byteEnd<<' ';
                        // }
                        // cout<<endl;
                    } else {
                        LOG(DEBUG,"---- data hole [%d,%d) cur %u----", iter->byteStart, iter->byteEnd, current);
                        parseInt(iter->byteStart,iter->byteEnd, -1, -1);//TODO priority
                        list<shared_ptr<IntcpSeg>>::iterator iter2;
                        for(iter2=int_buf.begin();iter2!=int_buf.end();iter2++){
                            // only if intSeg is fully covered
                            if(iter->byteStart<=(*iter2)->rangeStart
                                    && iter->byteEnd>=(*iter2)->rangeEnd){
                                (*iter2)->resendts = _getMillisec() + (*iter2)->rto;
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
                find_new_hole = true;
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
    return find_new_hole;
}

void IntcpTransCB::parseHopRttAsk(IUINT32 ts,IUINT32 sn,IUINT32 wnd){
    rmt_hop_rtt = (int)sn;
    rmt_cwnd = wnd;
    LOG(TRACE,"receive rmt hop rtt %d, rmt cwnd %d",rmt_hop_rtt,rmt_cwnd);
    IntcpSeg seg;
    seg.cmd = INTCP_CMD_HOP_RTT_TELL;
    seg.len = 0;
    seg.sn = 0;
    seg.ts = ts;
    //seg.rangeStart = 0;
    //seg.rangeEnd = 0;
    
    char *sendEnd=tmpBuffer.get();
    sendEnd = encodeSeg(tmpBuffer.get(),&seg);
    output(tmpBuffer.get(), (int)(sendEnd - tmpBuffer.get()), INTCP_REQUESTER);
    return;
}

void IntcpTransCB::parseData(shared_ptr<IntcpSeg> segPtr)
{

                
    // if(!isMidnode){
    // if(true){
    //     LOG(DEBUG,"rcv data [%d,%d)",segPtr->rangeStart,segPtr->rangeEnd);
    //     for(auto hole: dataHoles){
    //         LOG(DEBUG,"hole [%d,%d)",hole.byteStart,hole.byteEnd);
    //     }
    // }


    // //no rcv_wnd should be maintained on midnode
    // if (!isMidnode &&
    //         (_itimediff(sn, rcv_nxt + rcv_wnd) >= 0 ||
    //         _itimediff(sn, rcv_nxt) < 0)) {
    //     LOG(WARN,"recv a data seg out of rcv window");
    //     return;
    // }
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
                memcpy(intsecDataSeg->data+sizeof(IUINT32)*3, &intSeg->firstTs, sizeof(IUINT32));
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
                //---------------------------------
                IUINT32 current = _getMillisec();
                // if (intSeg->xmit==1 && _itimediff(current, intSeg->ts) >= 0) {
                //     updateRTT(_itimediff(current, intSeg->ts));
                //     LOG(TRACE,"rtt %ld srtt %d rto %d",_itimediff(current, intSeg->ts),rx_srtt,rx_rto);
                // }
                if(segPtr->ts != -1){
                    updateRTT(_itimediff(current, segPtr->ts));
                    LOG(TRACE,"rtt %ld srtt %d rto %d",_itimediff(current, intSeg->ts),rx_srtt,rx_rto);
                }
                //------------------------------
                // update int_buf
                //------------------------------
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
        if(nodeRole == INTCP_MIDNODE){
            shared_ptr<IntcpSeg> segToForward = createSeg(segPtr->len);
            memcpy(segToForward.get(),segPtr.get(),INTCP_OVERHEAD+segPtr->len);
            snd_queue.push_back(segToForward);
            // receiving by upper layer delete this seg, 
            // output also delete it, so we need two seg
            // in sendData(), the sn will be rewrite
            // sendData(data, rangeStart, rangeEnd);
        }
        rcv_buf.push_back(segPtr);
    }

    moveToRcvQueue();
    //TODO CC
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
        rmt_wnd = wnd;
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
        
        if (cmd != INTCP_CMD_PUSH && cmd != INTCP_CMD_INT &&
            cmd != INTCP_CMD_WASK && cmd != INTCP_CMD_WINS &&
            cmd != INTCP_CMD_HOP_RTT_ASK && cmd!= INTCP_CMD_HOP_RTT_TELL) 
            return -3;

        if(cmd==INTCP_CMD_INT){
            LOG(TRACE, "recv int [%d,%d)",rangeStart,rangeEnd);
            detectIntHole(rangeStart,rangeEnd,sn);
            parseInt(rangeStart,rangeEnd,ts,wnd);//TODO more CC information mighe be added.
            //rmt_wnd = wnd;
            //printf("remote window=%d\n",rmt_wnd);
        } else if (cmd == INTCP_CMD_PUSH) {
            // LOG(DEBUG, "input data sn %d [%d,%d)", sn, rangeStart,rangeEnd);
        
            // //EXPR
            // //simulate packet loss
            // if(isMidnode && sn%10==0){
            //     LOG(DEBUG,"drop sn %d [%d,%d)",sn,rangeStart,rangeEnd);
            //     data += len;
            //     size -= len;
            //     continue;
            // }


            // //avoid memcpy
            // if (isMidnode) {
            //     decode16u(dataOrg+sizeof(cmd),&wnd);
            //     outputFunc(dataOrg, sizeOrg, user, INTCP_REQUESTER);
            // }

            // if (isMidnode || 
            //         (_itimediff(sn, rcv_nxt + rcv_wnd) < 0 
            //         && _itimediff(sn, rcv_nxt) >= 0)
            //         ) {
            if(true){
                bool find_new_hole = detectDataHole(rangeStart,rangeEnd,sn);
                updateCwnd(find_new_hole,len);     //cc
                seg = createSeg(len);
                seg->cmd = cmd;
                seg->wnd = wnd;
                seg->ts = ts;
                seg->sn = sn;
                seg->len = len;
                seg->rangeStart = rangeStart;
                seg->rangeEnd = rangeEnd;
                memcpy(seg->data, data, len);

                parseData(seg);
            }
        }
        else if (cmd == INTCP_CMD_WASK) {
            // ready to send back INTCP_CMD_WINS in flush
            // tell remote my window size
            probe |= INTCP_ASK_TELL;
        }
        else if (cmd == INTCP_CMD_WINS) {
            // do nothing
        }
        
        else if (cmd == INTCP_CMD_HOP_RTT_ASK){
            LOG(TRACE,"recv hop rtt ask");
            parseHopRttAsk(ts,sn,wnd);
        }
        
        else if (cmd == INTCP_CMD_HOP_RTT_TELL){
            LOG(TRACE,"recv hop rtt tell");
            updateHopRtt(ts);
        }
        else {
            return -3;
        }

        data += len;
        size -= len;
    }
    
    /* CC, skip now
    if (_itimediff(snd_una, prev_una) > 0) {
        if (cwnd < rmt_wnd) {
            IUINT32 mss = mss;
            if (cwnd < ssthresh) {
                cwnd++;
                incr += mss;
            }    else {
                if (incr < mss) incr = mss;
                incr += (mss * mss) / incr + (mss / 16);
                if ((cwnd + 1) * mss <= incr) {
                #if 1
                    cwnd = (incr + mss - 1) / ((mss > 0)? mss : 1);
                #else
                    cwnd++;
                #endif
                }
            }
            if (cwnd > rmt_wnd) {
                cwnd = rmt_wnd;
                incr = rmt_wnd * mss;
            }
        }
    }
    */
    return 0;
}

//---------------------------------------------------------------------
// flush
//---------------------------------------------------------------------

void IntcpTransCB::flushWndProbe(){
    IUINT32 current = _getMillisec();
	char *sendEnd=tmpBuffer.get();
	// probe window size (if remote window size equals zero)
    if (rmt_wnd == 0) {
        if (probe_wait == 0) {        //first time rmt_wnd = 0
            probe_wait = INTCP_PROBE_INIT;
            ts_probe = current + probe_wait;
        }
        else {
            if (_itimediff(current, ts_probe) >= 0) {
                if (probe_wait < INTCP_PROBE_INIT) 
                    probe_wait = INTCP_PROBE_INIT;
                probe_wait += probe_wait / 2;
                if (probe_wait > INTCP_PROBE_LIMIT)
                    probe_wait = INTCP_PROBE_LIMIT;
                ts_probe = current + probe_wait;
                probe |= INTCP_ASK_SEND;
            }
        }
    }    else {
        ts_probe = 0;
        probe_wait = 0;
    }

    IntcpSeg seg;
    seg.wnd = getRwnd();
    seg.len = 0;
    seg.sn = 0;
    seg.ts = -1;

    // flush window probing commands
    if (probe & INTCP_ASK_SEND) {
        seg.cmd = INTCP_CMD_WASK;
        sendEnd = encodeSeg(tmpBuffer.get(), &seg);
		// responser asks requester
		output(tmpBuffer.get(), (int)(sendEnd - tmpBuffer.get()), INTCP_REQUESTER);
    }

    // flush window probing commands
    if (probe & INTCP_ASK_TELL) {
        seg.cmd = INTCP_CMD_WINS;
        sendEnd = encodeSeg(tmpBuffer.get(), &seg);
		output(tmpBuffer.get(), (int)(sendEnd - tmpBuffer.get()), INTCP_RESPONSER);
    }
	return;
}

void IntcpTransCB::flushHopRttAsk(){    //responder don't need
    IUINT32 current = _getMillisec();
	char *sendEnd=tmpBuffer.get();
	if (ts_hop_rtt_probe==0||_itimediff(current, ts_hop_rtt_probe) >= 0){
	    IntcpSeg seg;
        seg.wnd = getCwnd();
        seg.len = 0;
        seg.sn = hop_srtt;      //sn carry hop rtt, only for test
        seg.ts = current;
        seg.cmd = INTCP_CMD_HOP_RTT_ASK;
        //seg.cmd = INTCP_CMD_PUSH;
        sendEnd = encodeSeg(tmpBuffer.get(), &seg);
        output(tmpBuffer.get(), (int)(sendEnd - tmpBuffer.get()), INTCP_RESPONSER);
        LOG(TRACE,"send hop rtt flush");
	    ts_hop_rtt_probe = current+hop_rtt_probe_wait;
	}
}

void IntcpTransCB::flushIntQueue(){
    //TODO CC
    // int intRangeLimit = calcSendingWnd();
    int intRangeLimit = 65536;
    while(intRangeLimit>0 && !int_queue.empty()){
        shared_ptr<IntcpSeg> newseg = createSeg(0);
        assert(newseg);
        newseg->len = 0;
        newseg->sn = 0; // no need to use sn in interest
        newseg->cmd = INTCP_CMD_INT;
        
        newseg->wnd = getRwnd();
        //newseg->wnd = getCwnd();    //cc
        
        // resendts and rto will be set before output
        // newseg->resendts = current;
        // newseg->rto = rx_rto;
        newseg->xmit = 0;
        newseg->firstTs = _getMillisec();
        // LOG(DEBUG,"real cur %u int_cur %u",_getMillisec(),current);
        bool first = true;
        //NOTE assume that rangeEnd of interest in int_queue is in order
        for(list<IntRange>::iterator iter=int_queue.begin();iter!=int_queue.end();){
            if(first){
                newseg->rangeStart = iter->start;
                newseg->rangeEnd = _imin_(iter->end, newseg->rangeStart+intRangeLimit);
                first = false;
            } else {
                if(iter->start <= newseg->rangeEnd){
                    LOG(TRACE,"%u %u %u %u",newseg->rangeStart,newseg->rangeEnd,iter->start,iter->end);
                    newseg->rangeStart = _imin_(iter->start,newseg->rangeStart);
                    newseg->rangeEnd = _imin_(_imax_(newseg->rangeEnd, iter->end),
                            newseg->rangeStart+intRangeLimit);
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
        intRangeLimit -= newseg->rangeEnd-newseg->rangeStart;
        int_buf.push_back(newseg);
        // if(newseg->rangeEnd-newseg->rangeStart > 64){
        //     LOG(DEBUG,"%d %d",newseg->rangeStart,newseg->rangeEnd);
        // }
    }
}

void IntcpTransCB::flushIntBuf(){
    // calculate window size
    IUINT32 cwnd = _imin_(snd_wnd, rmt_wnd);
    //TODO CC
    // calculate resent
    int rtomin = (nodelay == 0)? (rx_rto >> 3) : 0;
	int rwnd = getRwnd();
    //int rwnd = getCwnd();
    int change = 0;
    int lost = 0;
	char *sendEnd=tmpBuffer.get();
	int sizeToSend=0;
    // from int_buf to udp
	list<shared_ptr<IntcpSeg>>::iterator p,next;
    for (p = int_buf.begin(); p != int_buf.end(); p=next) {
        next=p;next++;
        IUINT32 current = _getMillisec();
        shared_ptr<IntcpSeg> segPtr = *p;
        int needsend = 0;
        if(nodeRole == INTCP_MIDNODE){
            needsend = 1;
        } else {
            // RTO mechanism
            if (segPtr->xmit == 0) {
                needsend = 1;
                segPtr->rto = IUINT32(rx_rto*INTCP_RTO_FACTOR);
                // segPtr->resendts = current + segPtr->rto + rtomin;
                LOG(TRACE,"request [%d,%d) rto %d",segPtr->rangeStart,segPtr->rangeEnd, IUINT32(segPtr->rto*INTCP_RTO_FACTOR));
                segPtr->resendts = current + segPtr->rto;// + rtomin;
            } else if (_itimediff(current, segPtr->resendts) >= 0) {
                LOG(TRACE,"----- Timeout [%d,%d) xmit %d cur %u rto %d -----",
                        segPtr->rangeStart, segPtr->rangeEnd, segPtr->xmit, _getMillisec(),segPtr->rto);
                needsend = 1; //1 -> 0
                xmit++;
                if (nodelay == 0) { //this branch is default
                    segPtr->rto += _imax_(segPtr->rto, (IUINT32)rx_rto);
                } else {
                    IINT32 step = (nodelay < 2)? 
                        ((IINT32)(segPtr->rto)) : rx_rto;
                    segPtr->rto += step / 2;
                }
                segPtr->resendts = current + segPtr->rto;
                lost = 1;
            }
        }

        if (needsend) {
            //clear hole
            if(nodeRole != INTCP_MIDNODE){
            //DEBUG
            // if(false){
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
            int need;
            if(nodeRole == INTCP_REQUESTER){
                segPtr->ts = current;
            }
            segPtr->wnd = rwnd;
            segPtr->xmit++;
            segPtr->sn = snd_nxt_int++;
			sizeToSend = (int)(sendEnd - tmpBuffer.get());
            if (sizeToSend + (int)INTCP_OVERHEAD > (int)mtu) {
                output(tmpBuffer.get(), sizeToSend, INTCP_RESPONSER);
                sendEnd = tmpBuffer.get();
            }
            sendEnd = encodeSeg(sendEnd, segPtr.get());
            if (segPtr->xmit >= dead_link) {
                state = (IUINT32)-1;
                LOG(ERROR, "dead link");
                abort();
            }

            if(nodeRole == INTCP_MIDNODE){
                int_buf.erase(p);
            }
        }
    }

	// flush remain segments
    sizeToSend = (int)(sendEnd - tmpBuffer.get());
    if (sizeToSend > 0) {
        output(tmpBuffer.get(), sizeToSend, INTCP_RESPONSER);
    }

    //TODO CC: update info
    /*
    // update ssthresh
    if (change) {
        IUINT32 inflight = snd_nxt - snd_una;
        ssthresh = inflight / 2;
        if (ssthresh < INTCP_THRESH_MIN)
            ssthresh = INTCP_THRESH_MIN;
        cwnd = ssthresh + resent;
        incr = cwnd * mss;
    }

    if (lost) {
        ssthresh = cwnd / 2;
        if (ssthresh < INTCP_THRESH_MIN)
            ssthresh = INTCP_THRESH_MIN;
        cwnd = 1;
        incr = mss;
    }

    if (cwnd < 1) {
        cwnd = 1;
        incr = mss;
    }
    */
}

// snd_queue -> send straightforward;
void IntcpTransCB::flushData(){
    LOG(TRACE,"sendqueue len %lu",snd_queue.size());
    //TODO CC -- cwnd/sendingRate; design token bucket
    static int dataOutputLimit = 0;
    dataOutputLimit += getSendLimit();
    LOG(SILENT,"dataOutputLimit %d bytes",dataOutputLimit);
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
            reach_limit = true;
            break;
        }else{
            dataOutputLimit -= segPtr->len;
        }

		// responser doesn't need to tell requester its rwnd.
		// segPtr->wnd = seg.wnd;
		sizeToSend = (int)(sendEnd - tmpBuffer.get());
        if (sizeToSend + INTCP_OVERHEAD + segPtr->len > (int)mtu) {
            output(tmpBuffer.get(), sizeToSend, INTCP_REQUESTER);
            sendEnd = tmpBuffer.get();
        }

        LOG(TRACE,"sn %d [%d,%d) cur %u ts %u",segPtr->sn,segPtr->rangeStart,segPtr->rangeEnd,_getMillisec(),segPtr->ts);
        segPtr->sn = snd_nxt++;
        sendEnd = encodeSeg(sendEnd, segPtr.get());
        memcpy(sendEnd, segPtr->data, segPtr->len);
        sendEnd += segPtr->len;
        snd_queue.erase(p);
	}
	// flush remain segments
	if(!reach_limit)                //if cwnd is not enough for data, the remain wnd can use for next loop
	    dataOutputLimit = 0;
    sizeToSend = (int)(sendEnd - tmpBuffer.get());
    if (sizeToSend > 0) {
        output(tmpBuffer.get(), sizeToSend, INTCP_REQUESTER);
    }
}

void IntcpTransCB::flush(){
    // 'update' haven't been called. 
    
    if (updated == 0) return;
    
    
    
	//TODO flushWndProbe();
    if(nodeRole == INTCP_REQUESTER){
        flushIntQueue();
    }
    if(nodeRole != INTCP_RESPONSER){
        flushHopRttAsk();
    }
	flushIntBuf();
	flushData();
}


//---------------------------------------------------------------------
// update state (call it repeatedly, every 10ms-100ms), or you can ask 
// check when to call it again (without input/_send calling).
// 'current' - current timestamp in millisec. 
//---------------------------------------------------------------------
void IntcpTransCB::update()
{
    IUINT32 current = _getMillisec();
    if (updated == 0) {
        updated = 1;
        nextFlushTs = current;
    }

    IINT32 slap = _itimediff(current, nextFlushTs);

	if (slap>0 || slap<-10000){
        // LOG(DEBUG,"iq %ld ib %ld pit %ld sq %ld rb %ld rq %ld",
        //         int_queue.size(), int_buf.size(),recvedInts.size(),
        //         snd_queue.size(),rcv_buf.size(),rcv_queue.size());
        flush();

		if (slap >= updateInterval || slap < -10000) {
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
IUINT32 IntcpTransCB::check(IUINT32 current)
{
    IUINT32 _ts_flush = nextFlushTs;
    IINT32 tm_flush = 0x7fffffff;
    IINT32 tm_packet = 0x7fffffff;
    IUINT32 minimal = 0;
    list<shared_ptr<IntcpSeg>>::const_iterator p;

    if (updated == 0) {
        return current;
    }

    if (_itimediff(current, _ts_flush) >= 10000 ||
        _itimediff(current, _ts_flush) < -10000) {
        _ts_flush = current;
    }

    if (_itimediff(current, _ts_flush) >= 0) {
        return current;
    }

    tm_flush = _itimediff(_ts_flush, current);

    for (p = int_buf.begin(); p != int_buf.end(); p++) {
        IINT32 diff = _itimediff((*p)->resendts, current);
        if (diff <= 0) {
            return current;
        }
        if (diff < tm_packet) tm_packet = diff;
    }

    minimal = (IUINT32)(tm_packet < tm_flush ? tm_packet : tm_flush);
    if (minimal >= updateInterval) minimal = updateInterval;
    return current + minimal;
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
	if(cmd==INTCP_CMD_INT || cmd==INTCP_CMD_WINS || cmd==INTCP_CMD_HOP_RTT_ASK){
		return INTCP_RESPONSER;
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

//cc when send data
int IntcpTransCB::getSendLimit(){
    //return 65536;
    int limit;
    if(rmt_wnd==-1||rmt_hop_rtt==0||rmt_cwnd==0){    //haven't receive feedback
        limit =  INTCP_MTU_DEF;
    }        
    else{
        limit = (rmt_cwnd*INTCP_MTU_DEF*INTCP_INTERVAL)/rmt_hop_rtt;
        //LOG(TRACE,"wnd %d mtu %d interval %d hop rtt %d,send limit is %d bytes",rmt_wnd,INTCP_MTU_DEF,INTCP_INTERVAL,rmt_hop_rtt,limit);
        
    }
    return limit;
}

//cc
void IntcpTransCB::updateCwnd(bool is_hole,IUINT32 dataLen){
    static int cc_status = SLOW_START;
    static int ca_data_len = 0;     //bytes received in congestion avoid phase, when reach cwnd*mtu, cwnd++
    //LOG(SILENT,"cwnd %d mtu\n",cwnd);
    if(cc_status==SLOW_START){      //slow start
        if(is_hole){                //??
            cwnd = cwnd/2;
            if(cwnd<1)
                cwnd=1;
            ssthresh = max(cwnd,INTCP_THRESH_MIN);
            incr = cwnd*INTCP_MTU_DEF;
            cc_status == CONGESTION_AVOID;
        }
        else{
            incr += dataLen;        //window expand 1mss when receive 1mss data
            cwnd = incr/INTCP_MTU_DEF;
            if(cwnd>=ssthresh){     //entering ca
                ssthresh = cwnd;
                cc_status = CONGESTION_AVOID;
            }
        }
    }
    else if(cc_status==CONGESTION_AVOID){
        if(is_hole){
            ssthresh = max(ssthresh/2,INTCP_THRESH_MIN);
            cwnd = ssthresh;
            ca_data_len = 0;
        }
        else{
            ca_data_len += dataLen;
            if(ca_data_len>cwnd*INTCP_MTU_DEF){
                cwnd ++;
                ssthresh ++;
                incr += INTCP_MTU_DEF;
                ca_data_len = 0;
            }
        }
    }
}

IUINT32 IntcpTransCB::getCwnd(){
    return cwnd;
}
