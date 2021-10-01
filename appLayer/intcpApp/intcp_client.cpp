#include "../../intcp/include/api.h"
#include "config.h"
#include <thread>
#include <sys/time.h>
#undef LOG_LEVEL
#define LOG_LEVEL WARN

using namespace std;

void request_func(IntcpSess * _sessPtr){
    int sendStart = 0;
    while(1){
        //IUINT32 end = sendStart+REQ_LEN;
        _sessPtr->request(sendStart, sendStart+REQ_LEN);
        LOG(DEBUG,"  request range %d %d\n",sendStart,sendStart+REQ_LEN);
        sendStart += REQ_LEN;
        //std::this_thread::sleep_for(std::chrono::milliseconds(1000*REQ_INTV));
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
    int sendStart = 0;
    thread t(request_func,sessPtr);
    t.detach();
    int loop = 0;
    while(1){
        loop++;
        // send interest
        
       
        
        //IUINT32 sendEnd = sendStart+REQ_LEN;
        //sessPtr->request(sendStart, sendEnd);
        //printf("request %d %d\n",sendStart,sendEnd);
        //sendStart += sendEnd - sendStart;
        
        // recv data
        while(1){
            ret = sessPtr->recvData(recvBuf,MaxBufSize,&start,&end);
            if(loop%500==0)
                LOG(DEBUG,"---ret %d\n",ret);
            if(ret<0)
                continue;
            
            recvBuf[end-start]='\0';
            //DEBUG LOG(TRACE, "recv start %d end %d \"%s\"", start, end, recvBuf);
            //LOG(TRACE, "recv [%d,%d) \"%s\"", start, end, recvBuf);
            //printf("%d %d\n",start,end);
            
            int pos = _round_up(start,REQ_LEN);
            if(end-pos<sizeof(int))
                continue;
            IUINT32 sendTime = *((IUINT32 *)(recvBuf+pos-start));
            IUINT32 curTime = getMillisec();
            LOG(TRACE, "recv [%d,%d)\n", start, end);
            printf("recv [%d,%d) sendTime %u curTime %u owd_obs %u\n", start, end,sendTime,curTime, curTime-sendTime);
            fflush(stdout);
            //std::this_thread::sleep_for(std::chrono::milliseconds(100));
            usleep(100);//sleep 0.1ms
            //usleep(1000*REQ_INTV);
            //printf("fuck\n");
        }
        //usleep(1000*REQ_INTV);
        
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
