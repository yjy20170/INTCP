#ifndef __API_H__
#define __API_H__

#include "udp_intcp.h"

int chdirProgramDir();
void startRequester(Cache *cachePtr, ByteMap<IntcpSess*> *sessMapPtr, 
        void *(*onNewSess)(void* _sessPtr),//TODO remove this
        const char* ipStrReq, const char* ipStrResp, uint16_t respPort);
void startResponser(Cache *cachePtr, ByteMap<IntcpSess*> *sessMapPtr, 
        void *(*onNewSess)(void* _sessPtr), int (*onUnsatInt)(IUINT32 start, IUINT32 end, void *user),
        const char* ipStr, uint16_t port);
void startMidnode(Cache *cachePtr, ByteMap<IntcpSess*> *sessMapPtr, 
        void *(*onNewSess)(void* _sessPtr),
        uint16_t port);

        
#endif