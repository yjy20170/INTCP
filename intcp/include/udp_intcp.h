#ifndef __UDP_INTCP_H__
#define __UDP_INTCP_H__

#include "ikcp.h"
#include "ByteMap.h"
#include "cache.h"

#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>
#include <cstring>
#include <mutex>
#include <iostream>
#include <thread>



#define QUAD_STR_LEN 12 //4+2+4+2

#define DEFAULT_SERVER_PORT 5000
#define DEFAULT_MID_PORT 6000
#define DEFAULT_CLIENT_PORT 7000


using namespace std;

const int MaxBufSize = 3000;
const socklen_t AddrLen = (socklen_t)(sizeof(struct sockaddr_in));

/***************** util functions *****************/

void get_current_time(long *sec, long *usec);
IUINT32 getMillisec();
struct sockaddr_in toAddr(in_addr_t IP, uint16_t port);
bool addrCmp(struct sockaddr_in addr1, struct sockaddr_in addr2);
void writeIPstr(char *ret, in_addr_t address);

int createSocket(in_addr_t IP, uint16_t port);
int createSocket(in_addr_t IP, uint16_t port, int portRange, uint16_t *finalPort);

/***************** INTCP session *****************/

class Quad
{
public:
    in_addr_t reqAddrIP;
    uint16_t reqAddrPort;
    in_addr_t respAddrIP;
    uint16_t respAddrPort;
    
    char chars[QUAD_STR_LEN];
    Quad(in_addr_t _reqAddrIP, uint16_t _reqAddrPort, in_addr_t _respAddrIP, uint16_t _respAddrPort);
    Quad(struct sockaddr_in requesterAddr, struct sockaddr_in responserAddr);
    Quad reverse();
    void toChars();
    struct sockaddr_in getReqAddr();
    struct sockaddr_in getRespAddr();

    bool operator == (Quad const& quad2) const;
};
class IntcpSess{
public:
    int socketFd_toReq, socketFd_toResp;
    struct sockaddr_in requesterAddr, responserAddr;
    char nameChars[QUAD_STR_LEN];
    int nodeRole;
    IntcpTransCB *transCB;
    // IntcpTransCB *transCB_resp;
    Cache *cachePtr;
    mutex lock;
    pthread_t transUpdaterThread, onNewSessThread;
    // pthread_t TransUpdater_resp;

    //requester
    IntcpSess(in_addr_t reqAddrIP, in_addr_t respAddrIP, 
        uint16_t respAddrPort, Cache* _cachePtr,
        void *(*onNewSess)(void* _sessPtr));
    //responser
    IntcpSess(Quad quad, int listenFd, Cache* _cachePtr,
        void *(*onNewSess)(void* _sessPtr),int (*onUnsatInt)(IUINT32 start, IUINT32 end, void *user));
    //midnode
    IntcpSess(Quad quad, Cache* _cachePtr,
        void *(*onNewSess)(void* _sessPtr));
    
    int inputUDP(char *recvBuf, int recvLen);
    void request(int rangeStart, int rangeEnd);
    int recvData(char *recvBuf, int maxBufSize, IUINT32 *startPtr, IUINT32 *endPtr);
    void insertData(const char *sendBuf, int start, int end);
};
void* TransUpdateLoop(void *args);
int udpSend(const char* buf,int len, void* user, int dstRole);
int fetchData(char *buf, IUINT32 start, IUINT32 end, void *user);
IntcpTransCB* createTransCB(const IntcpSess *sessPtr, bool isMidnode, int (*onUnsatInt)(IUINT32 start, IUINT32 end, void *user));

/***************** multi-session management *****************/


struct udpRecvLoopArgs
{
    ByteMap<IntcpSess*> *sessMapPtr;
    void* (*onNewSess)(void*);
    int (*onUnsatInt)(IUINT32 start, IUINT32 end, void *user);
    struct sockaddr_in listenAddr;
    int listenFd=-1;
    Cache* cachePtr;
};
void *udpRecvLoop(void *_args);

#endif