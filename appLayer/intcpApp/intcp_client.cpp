#include "../../intcp/include/api.h"
#include "config.h"
#include <thread>
#include <sys/time.h>
#undef LOG_LEVEL
#define LOG_LEVEL DEBUG

using namespace std;

void request_func(IntcpSess * _sessPtr){
    int sendStart = 0;
    while(1){
        _sessPtr->request(sendStart, sendStart+REQ_LEN);
        LOG(TRACE,"request range [%d,%d)",sendStart,sendStart+REQ_LEN);
        sendStart += REQ_LEN;
        usleep(1000*REQ_INTV);
    }
}

int _round_up(int x,int y){
    return ((x+y-1)/y)*y;
}

void *onNewSess(void* _sessPtr){
    IntcpSess *sessPtr = (IntcpSess*)_sessPtr;
    
    int ret;
    char recvBuf[MaxBufSize];
    IUINT32 start,end;
    
    thread t(request_func,sessPtr);
    t.detach();
    
    while(1){
        usleep(10);//sleep 0.1ms
        
        ret = sessPtr->recvData(recvBuf,MaxBufSize,&start,&end);
        
        if(ret<0)
            continue;
        
        recvBuf[end-start]='\0';
        
        int pos = _round_up(start,REQ_LEN);
        if(end-pos<sizeof(int))
            continue;
        IUINT32 sendTime = *((IUINT32 *)(recvBuf+pos-start));
        IUINT32 curTime = getMillisec();
        LOG(TRACE, "recv [%d,%d)\n", start, end);

        printf("recv %d [%d,%d) sendTime %u curTime %u owd_obs %u\n", end-start,start, end,sendTime,curTime, curTime-sendTime);
        if(curTime-sendTime > 2000){
            assert(false);
        }
        fflush(stdout);
    }

    return nullptr;
}

int main(){
    Cache cache(QUAD_STR_LEN);
    ByteMap<IntcpSess*> sessMap;
    startRequester(&cache,&sessMap,onNewSess,
        "10.0.1.1","10.0.100.2",DEFAULT_SERVER_PORT);
    return 0;
}
