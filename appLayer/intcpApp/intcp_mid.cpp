#include "../../intcp/include/api.h"
#undef LOG_LEVEL
#define LOG_LEVEL DEBUG

void *onNewSess(void* _sessPtr){
    IntcpSess *sessPtr = (IntcpSess*)_sessPtr;
    char reqIP[30],respIP[30];
    writeIPstr(reqIP, sessPtr->requesterAddr.sin_addr.s_addr);
    writeIPstr(respIP, sessPtr->responserAddr.sin_addr.s_addr);
    LOG(DEBUG,"new sess req %s:%d resp %s:%d",
            reqIP,
            ntohs(sessPtr->requesterAddr.sin_port),
            respIP,
            ntohs(sessPtr->responserAddr.sin_port)
    );
    
    char recvBuf[MaxBufSize];
    while(1){
        int ret;
        IUINT32 start,end;
        ret = sessPtr->recvData(recvBuf, MaxBufSize, &start, &end);
        if(ret >= 0){
            sessPtr->cachePtr->insert(sessPtr->nameChars,start,end,recvBuf);
        }
    }
    
    return nullptr;
}

int main(){
    Cache cache(QUAD_STR_LEN);
    ByteMap<IntcpSess*> sessMap;

    startMidnode(&cache,&sessMap,onNewSess,DEFAULT_MID_PORT);
    
    return 0;
}