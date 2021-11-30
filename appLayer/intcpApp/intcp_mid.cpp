#include "../../intcp/include/api.h"
#undef LOG_LEVEL
#define LOG_LEVEL DEBUG

void *onNewSess(void* _sessPtr){
    IntcpSess *sessPtr = (IntcpSess*)_sessPtr;
    char reqIP[30],respIP[30];
    writeIPstr(reqIP, sessPtr->requesterAddr.sin_addr.s_addr);
    writeIPstr(respIP, sessPtr->responderAddr.sin_addr.s_addr);
    LOG(DEBUG,"new sess req %s:%d resp %s:%d",
            reqIP,
            ntohs(sessPtr->requesterAddr.sin_port),
            respIP,
            ntohs(sessPtr->responderAddr.sin_port)
    );
    
    char recvBuf[MaxBufSize];
    IUINT32 start,end;
    while(1){
        while(sessPtr->recvData(recvBuf, MaxBufSize, &start, &end) == 0){
            sessPtr->cachePtr->insert(sessPtr->nameChars,start,end,recvBuf);
        }
        usleep(1000);
    }
    
    return nullptr;
}

int main(){
    Cache cache(QUAD_STR_LEN);
    ByteMap<shared_ptr<IntcpSess>> sessMap;
    printf("entering intcpm\n");
    fflush(stdout);
    startMidnode(&cache,&sessMap,onNewSess,DEFAULT_MID_PORT);
    
    return 0;
}
