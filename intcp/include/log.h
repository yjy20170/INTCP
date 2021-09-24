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
        printf("[%s|%s@%s, %d]\n        " format "\n", \
                #level, __func__, ptrL, \
                __LINE__, ##__VA_ARGS__); \
    }

        // const char *ptrR = strrchr(fileStr, '.'); 
        // printf("[%s|%s@%*.*s, %d] " format "\n", 
        //             levelStr, __func__, (int)(ptrR-ptrL), (int)(ptrR-ptrL), ptrL, 
        //             __LINE__, ##__VA_ARGS__); 
#endif