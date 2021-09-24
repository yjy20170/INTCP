#include "../../intcp/include/api.h"
#include "config.h"
#undef LOG_LEVEL
#define LOG_LEVEL DEBUG

void *onNewSess(void* _sessPtr){
    IntcpSess *sessPtr = (IntcpSess*)_sessPtr;
    
    int ret;
    char recvBuf[MaxBufSize];
    IUINT32 start,end;
    int sendStart = 0;
    while(1){
        // send interest
        if(sendStart<TOTAL_DATA_LEN){
            IUINT32 end = _imin_(sendStart+REQ_LEN, TOTAL_DATA_LEN);
            sessPtr->request(sendStart, end);
            sendStart += end - sendStart;
        }
        
        // recv data
        while(1){
            ret = sessPtr->recvData(recvBuf,MaxBufSize,&start,&end);
            if(ret<0)
                break;
            recvBuf[end-start]='\0';
            //DEBUG LOG(TRACE, "recv start %d end %d \"%s\"", start, end, recvBuf);
            LOG(TRACE, "recv [%d,%d) \"%s\"", start, end, recvBuf);
            usleep(1000);//sleep 1ms
        }
        usleep(1000*REQ_INTV);
    }

    return nullptr;
}

int main(){
    Cache cache(QUAD_STR_LEN);
    ByteMap<IntcpSess*> sessMap;
    startRequester(&cache,&sessMap,onNewSess,
        "10.0.1.1","10.0.2.1",DEFAULT_SERVER_PORT);
    return 0;
}