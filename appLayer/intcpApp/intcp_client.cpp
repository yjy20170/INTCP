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
        while(1){
            if(end-pos<sizeof(IUINT32)*2)
                break;
            //printf("%d %d %d\n",pos,start,end);
            IUINT32 sendTime = *((IUINT32 *)(recvBuf+pos-start));
            IUINT32 xmit = *((IUINT32 *)(recvBuf+pos-start+sizeof(IUINT32)));
            IUINT32 recvTime = *((IUINT32 *)(recvBuf+pos-start+sizeof(IUINT32)*2));
            IUINT32 firstTs = *((IUINT32 *)(recvBuf+pos-start+sizeof(IUINT32)*3));
            IUINT32 curTime = getMillisec();
            LOG(TRACE, "recv [%d,%d)\n", start, end);

            // if(recvTime<1000){
                printf("recv [%d,%d) xmit %u intcpRtt %u owd_noOrder %u sendTime %u recvTime %u curTime %u owd_obs %u\n", pos,pos+REQ_LEN,xmit,recvTime-firstTs,recvTime-sendTime,sendTime,recvTime,curTime, curTime-sendTime);
                // abort();
            // }
            fflush(stdout);
            /*
            if(recvTime<1000){
                printf("recv [%d,%d) xmit %u rto %u owd_noOrder %u sendTime %u recvTime %u curTime %u owd_obs %u\n", pos,pos+REQ_LEN,xmit,rto,recvTime-sendTime,sendTime,recvTime,curTime, curTime-sendTime);
                //printf("%d %d %d\n",pos,start,end);
                fflush(stdout);
            
            }
            */
            pos += REQ_LEN;
        }
        

    }

    return nullptr;
}

int main(){
    Cache cache(QUAD_STR_LEN);
    ByteMap<shared_ptr<IntcpSess>> sessMap;
    printf("entering intcpc\n");
    startRequester(&cache,&sessMap,onNewSess,
        "10.0.1.1","10.0.100.2",DEFAULT_SERVER_PORT);
    //printf(_round_up())
    return 0;
}
