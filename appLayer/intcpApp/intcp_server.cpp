#include "../../intcp/include/api.h"
#include "config.h"
#undef LOG_LEVEL
#define LOG_LEVEL DEBUG

void *onNewSess(void* _sessPtr){
    // LOGL(DEBUG);
    IntcpSess *sessPtr = (IntcpSess*)_sessPtr;
    char dataBuf[TOTAL_DATA_LEN];
    for(int ptr = 0; ptr<TOTAL_DATA_LEN; ptr++){
        if(ptr%10==0){
            dataBuf[ptr]='a'+(ptr/10)%10;
        }else{
            dataBuf[ptr]='0'+ptr%10;
        }
    }
    LOG(TRACE, "insert start=%d end=%d",0,TOTAL_DATA_LEN);
    sessPtr->insertData(dataBuf, 0, TOTAL_DATA_LEN);
    return nullptr;
}

int main(){
    Cache cache(QUAD_STR_LEN);
    ByteMap<IntcpSess*> sessMap;

    startResponser(&cache,&sessMap,onNewSess,
            "10.0.2.1", DEFAULT_SERVER_PORT);

    // udpRecvLoop(&args);
    return 0;
}