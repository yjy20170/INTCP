#ifndef __LOG_H__
#define __LOG_H__

#include <stdio.h>
#include <string.h>

#define TRACE 1
#define DEBUG 3
#define WARN 5
#define ERROR 7
#define SILENT 10

#define LOG_LEVEL DEBUG


#define LOGL(level) \
    if(level>=LOG_LEVEL){ \
        char fileStr[100]{__FILE__}; \
        const char *ptrL = strrchr(fileStr,'/'); \
        if(ptrL==NULL) { \
            ptrL = fileStr; \
        }else{ \
            ptrL++; \
        } \
        printf("[%s|%s@%s, %d]\n", \
                #level, __func__, ptrL, \
                __LINE__); \
    }

#define LOG(level, format, ...) \
    if(level>=LOG_LEVEL){ \
        char fileStr[100]{__FILE__}; \
        const char *ptrL = strrchr(fileStr,'/'); \
        if(ptrL==NULL) { \
            ptrL = fileStr; \
        }else{ \
            ptrL++; \
        } \
        int limit = 30; \
        char prefix[limit+4]; \
        memset(prefix,' ',limit+4); \
        snprintf(prefix, limit+1, "%s@%s,%d", \
                __func__, ptrL, __LINE__); \
        prefix[strlen(prefix)]=' '; \
        prefix[limit+1] = '|'; \
        prefix[limit+3] = '\0'; \
        printf("%s" format "\n",prefix,##__VA_ARGS__); \
    }

#endif