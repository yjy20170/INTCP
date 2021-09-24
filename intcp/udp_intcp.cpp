#include "./include/udp_intcp.h"
#undef LOG_LEVEL
#define LOG_LEVEL DEBUG


/***************** util functions *****************/

void get_current_time(long *sec, long *usec)
{
    struct timeval time;
    gettimeofday(&time, NULL);
    if (sec) *sec = time.tv_sec;
    if (usec) *usec = time.tv_usec;
}

IUINT32 getMillisec(){
    long sec,usec;
    IINT64 res;
    get_current_time(&sec,&usec);
    res = ((IINT64)sec) * 1000 + (usec / 1000);
    return (IUINT32)(res & 0xfffffffful);
}

struct sockaddr_in toAddr(in_addr_t IP, uint16_t port) {
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = IP;
    addr.sin_port = port;
    return addr;
}

void writeIPstr(char *ret, in_addr_t IP)
{
    int a,b,c,d;

    a = (0x000000FF & IP);
    b = (0x0000FF00 & IP) >> 8;
    c = (0x00FF0000 & IP) >> 16;
    d = (0xFF000000 & IP) >> 24;

    snprintf(ret,16,"%d.%d.%d.%d",a,b,c,d);
}

/***************** Quad *****************/
// numbers stored in Quad is in type for network ( hton() )
// quadruple for end2end communication
Quad::Quad(in_addr_t _reqAddrIP, uint16_t _reqAddrPort, in_addr_t _respAddrIP, uint16_t _respAddrPort):
reqAddrIP(_reqAddrIP),
reqAddrPort(_reqAddrPort),
respAddrIP(_respAddrIP),
respAddrPort(_respAddrPort)
{
    toChars();
}
Quad::Quad(struct sockaddr_in requesterAddr, struct sockaddr_in responserAddr):
        reqAddrIP(requesterAddr.sin_addr.s_addr), reqAddrPort(requesterAddr.sin_port), respAddrIP(responserAddr.sin_addr.s_addr), respAddrPort(responserAddr.sin_port){
    toChars();
}

Quad Quad::reverse(){
    return Quad(respAddrIP,respAddrPort,reqAddrIP,reqAddrPort);
}
void Quad::toChars(){
    int offset = 0;
    
    memcpy(this->chars+offset, &this->reqAddrIP, sizeof(this->reqAddrIP));
    offset += sizeof(this->reqAddrIP);
    memcpy(this->chars+offset, &this->reqAddrPort, sizeof(this->reqAddrPort));
    offset += sizeof(this->reqAddrPort);
    memcpy(this->chars+offset, &this->respAddrIP, sizeof(this->respAddrIP));
    offset += sizeof(this->respAddrIP);
    memcpy(this->chars+offset, &this->respAddrPort, sizeof(this->respAddrPort));

    // int check=0;
    // for(int i=0;i<QUAD_STR_LEN;i++) {
    //     cout<<(int)chars[i]<<' ';
    //     check+=chars[i];
    // }
    // cout<<endl;
    // cout<<"toChars() "<<check<<' '<<reqAddrIP<<' '<<reqAddrPort<<' '<<respAddrIP<<' '<<respAddrPort<<endl;
}

struct sockaddr_in Quad::getReqAddr(){
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = reqAddrIP;
    addr.sin_port = reqAddrPort;
    return addr;
}
struct sockaddr_in Quad::getRespAddr(){
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = respAddrIP;
    addr.sin_port = respAddrPort;
    return addr;
}
bool Quad::operator == (Quad const& quad2) const {
    // if (reqAddrIP == quad2.reqAddrIP
    //     && reqAddrPort == quad2.reqAddrPort
    //     && respAddrIP == quad2.respAddrIP
    //     && respAddrPort == quad2.respAddrPort )
    //     return true;
    // return false;
    return memcmp(this->chars, quad2.chars, QUAD_STR_LEN)==0 ? true : false;
}



/***************** INTCP session *****************/

int createSocket(in_addr_t IP, uint16_t port){
    return createSocket(IP, port, 1, nullptr);
}
int createSocket(in_addr_t IP, uint16_t port, int portRange, uint16_t *finalPort){
    int socketFd = -1;
    if((socketFd=socket(AF_INET,SOCK_DGRAM,0))<0){
        LOG(ERROR, "create socket fail");
        return -1;
    }
    int optval=1;
    setsockopt(socketFd, SOL_SOCKET, SO_REUSEADDR, &optval, sizeof(int));
    setsockopt(socketFd, SOL_IP, IP_TRANSPARENT, &optval, sizeof(int));
    setsockopt(socketFd, SOL_IP, IP_RECVORIGDSTADDR, &optval, sizeof(int));
    sockaddr_in selfAddr;
    selfAddr.sin_family = AF_INET;
    selfAddr.sin_addr.s_addr = IP;
    uint16_t realPortH = ntohs(port);
    for(;realPortH < ntohs(port)+portRange; realPortH++){
        selfAddr.sin_port = htons(realPortH);
        if(bind(socketFd, (struct sockaddr *)&selfAddr, AddrLen) != -1){
            break;
        }
    }
    // which means all the ports in portRange bind fail
    if(realPortH == ntohs(port)+portRange){
        LOG(ERROR, "bind fail");
        return -1;
    }

    if(finalPort != nullptr)
        *finalPort = htons(realPortH);
    return socketFd;
}

// this is for [requester]
// explicitly called by app-layer
IntcpSess::IntcpSess(in_addr_t reqAddrIP, in_addr_t respAddrIP, 
        uint16_t respAddrPort, Cache* _cachePtr,
        void *(*onNewSess)(void* _sessPtr)):
nodeRole(INTCP_REQUESTER),
cachePtr(_cachePtr)
{
    uint16_t reqAddrPort;
    socketFd_toResp = createSocket(reqAddrIP, htons(DEFAULT_CLIENT_PORT), 1000, &reqAddrPort);
    if(socketFd_toResp == -1){
        abort();
    }
    socketFd_toReq = -1;

    requesterAddr = toAddr(reqAddrIP, reqAddrPort);
    responserAddr = toAddr(respAddrIP, respAddrPort);

    //general
    Quad quad(requesterAddr,responserAddr);
    memcpy(nameChars, quad.chars, QUAD_STR_LEN);
    lock.lock();
    transCB = createTransCB(this, nodeRole==INTCP_MIDNODE);
    lock.unlock();
    pthread_create(&transUpdaterThread, NULL, TransUpdateLoop, this);
    pthread_create(&onNewSessThread, NULL, onNewSess, this);
    return;
}

// this is for [responser]
// this is called when receiving a new Quad
IntcpSess::IntcpSess(Quad quad, int listenFd, Cache* _cachePtr,
        void *(*onNewSess)(void* _sessPtr)):
nodeRole(INTCP_RESPONSER),
cachePtr(_cachePtr)
{
    requesterAddr = quad.getReqAddr();
    responserAddr = quad.getRespAddr();
    
    socketFd_toReq = listenFd;
    socketFd_toResp = -1;


    memcpy(nameChars, quad.chars, QUAD_STR_LEN);
    lock.lock();
    transCB = createTransCB(this, nodeRole==INTCP_MIDNODE);
    lock.unlock();
    pthread_create(&transUpdaterThread, NULL, TransUpdateLoop, this);
    pthread_create(&onNewSessThread, NULL, onNewSess, this);
    return;
}

// this is for [midnode]
// this is called when receiving a new Quad
IntcpSess::IntcpSess(Quad quad, Cache* _cachePtr,
        void *(*onNewSess)(void* _sessPtr)):
nodeRole(INTCP_MIDNODE),
cachePtr(_cachePtr)
{
    requesterAddr = quad.getReqAddr();
    responserAddr = quad.getRespAddr();
    
    socketFd_toReq = createSocket(responserAddr.sin_addr.s_addr, responserAddr.sin_port);
    socketFd_toResp = createSocket(requesterAddr.sin_addr.s_addr, requesterAddr.sin_port);
    if(socketFd_toReq==-1 || socketFd_toResp)
    memcpy(nameChars, quad.chars, QUAD_STR_LEN);
    lock.lock();
    transCB = createTransCB(this, nodeRole==INTCP_MIDNODE);
    lock.unlock();
    pthread_create(&transUpdaterThread, NULL, TransUpdateLoop, this);
    pthread_create(&onNewSessThread, NULL, onNewSess, this);
    return;
}


int IntcpSess::inputUDP(char *recvBuf, int recvLen){
    lock.lock();
    int ret;
    ret = transCB->input(recvBuf, recvLen);
    lock.unlock();
    return ret;
}

void IntcpSess::request(int rangeStart, int rangeEnd){
    lock.lock();
    transCB->request(rangeStart,rangeEnd);
    lock.unlock();
}
int IntcpSess::recvData(char *recvBuf, int maxBufSize, IUINT32 *startPtr, IUINT32 *endPtr){
    lock.lock();
    int ret = transCB->recv(recvBuf,maxBufSize, startPtr, endPtr);
    lock.unlock();
    return ret;
}
void IntcpSess::insertData(const char *sendBuf, int start, int end){
    // transCB->send(sendBuf,end-start);
    int ret=cachePtr->insert(nameChars,start,end,sendBuf);
    assert(ret==0);
    lock.lock();
    transCB->notifyNewData(start,end,getMillisec());
    lock.unlock();
}
void* TransUpdateLoop(void *args){
    IntcpSess *sessPtr = (IntcpSess*)args;

    // IUINT32 lastUpdateTime = -1;
    IUINT32 now, updateTime;
    while(1){
        now = getMillisec();
        sessPtr->lock.lock();
        updateTime = sessPtr->transCB->check(now);
        if (updateTime <= now) {
            // if(lastUpdateTime!=-1){
            //     LOG(DEBUG,"update interval %d", now - lastUpdateTime);
            // }
            // lastUpdateTime = now;
            sessPtr->transCB->update(now);
            sessPtr->lock.unlock();
        } else {
            sessPtr->lock.unlock();
            usleep((updateTime - now + 1)*1000);
            continue;
        }
    }
    return nullptr;
}
IntcpTransCB* createTransCB(const IntcpSess *sessPtr, bool isMidnode){
    IntcpTransCB* transCB = new IntcpTransCB((void*)sessPtr, udpSend, fetchData, isMidnode);
    
    //set transCB paramaters
    // transCB->setNoDelay(1, 5, 2, 1);
    // transCB->setWndSize(10,128);
    // transCB->setMtu(20);
    return transCB;
}

int udpSend(const char* buf,int len, void* user, int dstRole){
    IntcpSess* sess = (IntcpSess*)user;
    if(sess->nodeRole == dstRole){
        LOG(ERROR, "sess->nodeRole == dstRole");
        abort();
        return -1;
    }
    struct sockaddr_in *dstAddrPtr;
    int outputFd;
    if(dstRole==INTCP_RESPONSER){
        dstAddrPtr = &sess->responserAddr;
        outputFd = sess->socketFd_toResp;
    }else if(dstRole==INTCP_REQUESTER){
        //in midnode, udpSend_default send to requester and udpSend_toResp send to responser
        dstAddrPtr = &sess->requesterAddr;
        outputFd = sess->socketFd_toReq;
    } else {
        LOG(ERROR, "dstRole must be an endpoint");
        abort();
        return -1;
    }
    if(outputFd == -1){
        LOG(ERROR, "outputFd == -1");
        return -1;
    }
    int sendbyte = sendto(outputFd, buf, len, 0, 
            (struct sockaddr*)dstAddrPtr, AddrLen);

    char recvIP[25];
    writeIPstr(recvIP, dstAddrPtr->sin_addr.s_addr);
    LOG(TRACE, "send %d bytes to %s:%d",len, recvIP, ntohs(dstAddrPtr->sin_port));
    return sendbyte;
}

int fetchData(char *buf, IUINT32 start, IUINT32 end, void *user){
    IntcpSess* sess = (IntcpSess*)user;
    int readlen = sess->cachePtr->read(sess->nameChars, start, end, buf);
    return readlen;
}


/***************** multi-session management *****************/


bool addrCmp(struct sockaddr_in addr1, struct sockaddr_in addr2){
    return (addr1.sin_addr.s_addr == addr2.sin_addr.s_addr) && (addr1.sin_port == addr2.sin_port);
}


void *udpRecvLoop(void *_args){
    struct udpRecvLoopArgs *args = (struct udpRecvLoopArgs *)_args;
    char recvBuf[MaxBufSize];
    int recvLen;

    // first, create a socket for listening
    int listenFd;
    if (args->listenFd == -1){
        listenFd = createSocket(
                args->listenAddr.sin_addr.s_addr, args->listenAddr.sin_port);
    } else {
        listenFd = args->listenFd;
    }

    // prepare for udp recv
    struct sockaddr_in sendAddr, recvAddr, requesterAddr, responserAddr;
    char cmbuf[100];

    struct iovec iov;
    iov.iov_base = recvBuf;
    iov.iov_len = sizeof(recvBuf) - 1;
    struct msghdr mhdr;
    mhdr.msg_name = &sendAddr;
    mhdr.msg_namelen = AddrLen;
    mhdr.msg_control = cmbuf;
    mhdr.msg_controllen = 100;
    mhdr.msg_iovlen = 1;
    mhdr.msg_iov = &iov;

    IntcpSess *sessPtr;
    while(1){
        // int recvLen = recvfrom(
        //     listenFd,
        //     recvBuf,sizeof(recvBuf),
        //     MSG_DONTWAIT,
        //     (struct sockaddr*)&recvAddr, // for server, get remote addr here
        //     nullptr
        // );

        recvLen = recvmsg(listenFd, &mhdr, 0);

        for(struct cmsghdr *cmsg = CMSG_FIRSTHDR(&mhdr); cmsg != NULL; cmsg = CMSG_NXTHDR(&mhdr, cmsg)){
            if(cmsg->cmsg_level != SOL_IP || cmsg->cmsg_type != IP_ORIGDSTADDR) continue;
            memcpy(&recvAddr, CMSG_DATA(cmsg), sizeof(struct sockaddr_in));
        }
        LOG(TRACE, "recv udp len=%d",recvLen);

        // now we get: data in recvBuf, recvLen, sendAddr, recvAddr

        bool isEndp = addrCmp(recvAddr, args->listenAddr);
        int segDstRole = IntcpTransCB::judgeSegDst(recvBuf, recvLen);
        
        if(segDstRole == INTCP_RESPONSER){
            requesterAddr = sendAddr;
            responserAddr = recvAddr;
        } else if (segDstRole == INTCP_REQUESTER) {
            requesterAddr = recvAddr;
            responserAddr = sendAddr;
        } else {
            LOG(WARN,"recv not-INTCP packet");
            //TODO forward to recvAddr;
            //TODO dst of some pkts can be midnode in future.
            continue;
        }
        Quad quad(requesterAddr, responserAddr);
        int ret = args->sessMapPtr->readValue(quad.chars, QUAD_STR_LEN, &sessPtr);
        if (ret == -1){
            //if the endpoint receives a intcp DATA packet from unknown session, ignores it.
            if(isEndp && segDstRole==INTCP_REQUESTER){
                LOG(WARN,"requester recvs an unknown packet");
                continue;
            }
            // if not exist, create one.
            char sendIPstr[25];
            writeIPstr(sendIPstr, sendAddr.sin_addr.s_addr);
            LOG(TRACE,"establish: %s:%d", sendIPstr, ntohs(sendAddr.sin_port));
            if(isEndp){
                //new responser session
                sessPtr = new IntcpSess(quad, listenFd, args->cachePtr, args->onNewSess);
            } else {
                //new midnode session
                sessPtr = new IntcpSess(quad, args->cachePtr, args->onNewSess);
            }
             //nodeRole=server
            args->sessMapPtr->setValue(quad.chars, QUAD_STR_LEN, sessPtr);
        }
        sessPtr->inputUDP(recvBuf, recvLen);
    }

    return nullptr;
}