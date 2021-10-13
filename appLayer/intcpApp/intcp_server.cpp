#include "../../intcp/include/api.h"
#include "config.h"
#include <string.h>
#include <sys/time.h>
#undef LOG_LEVEL
#define LOG_LEVEL DEBUG



void *onNewSess(void* _sessPtr){
    // LOGL(DEBUG);
    IntcpSess *sessPtr = (IntcpSess*)_sessPtr;
    char dataBuf[TOTAL_DATA_LEN];
    
    /*
    for(int ptr = 0; ptr<TOTAL_DATA_LEN; ptr++){
        if(ptr%10==0){
            dataBuf[ptr]='a'+(ptr/10)%10;
        }else{
            dataBuf[ptr]='0'+ptr%10;
        }
    }
    LOG(TRACE, "insert start=%d end=%d",0,TOTAL_DATA_LEN);
    sessPtr->insertData(dataBuf, 0, TOTAL_DATA_LEN);
    */
    
    
    //int len = 10;
    int start = 0;
    while(1){
        memset(dataBuf,0,REQ_LEN);
        *((IUINT32 *)dataBuf) = getMillisec();
        sessPtr->insertData(dataBuf,start,start+REQ_LEN);
        LOG(TRACE,"insert %d %d\n",start,start+REQ_LEN);
        start += REQ_LEN;
        usleep(1.1*1000*REQ_INTV);
        //printf("abcde\n");
    }
    
    /*
    memset(dataBuf,0,sizeof(dataBuf));
    for(int ptr = 0; ptr<TOTAL_DATA_LEN; ptr+=10){
        *((IUINT32 *)(dataBuf+ptr)) = getMillisec();
    }
    LOG(TRACE, "insert start=%d end=%d",0,TOTAL_DATA_LEN);
    sessPtr->insertData(dataBuf, 0, TOTAL_DATA_LEN);
    */
    return nullptr;
}

int main(){
    Cache cache(QUAD_STR_LEN);
    ByteMap<IntcpSess*> sessMap;

    startResponser(&cache,&sessMap,onNewSess,
            "10.0.100.2", DEFAULT_SERVER_PORT);

    // udpRecvLoop(&args);
    return 0;
}
