#ifndef __CACHE_H__
#define __CACHE_H__

#include "ByteMap.h"
#include "generality.h"
#include "log.h"

#include <list>
#include <mutex>

using namespace std;

// #include <queue>

#define BLOCK_LEN 4096
#define BLOCK_SEG_NUM 10
#define MAX_BLOCK_NUM 10000 // 40MB

struct Block;
struct Node{
    ByteMap<Block*>::iterator blockIter;
};
struct Block {
    char dataPtr[BLOCK_LEN];
    IUINT32 ranges[BLOCK_SEG_NUM*2];
    list<Node>::iterator nodeIter;
};
// struct BlockInfo {
//     ByteMap<Block>::iterator iter;
//     IUINT32 lastTime;
// };
// struct cmp{
//     bool operator()(BlockInfo a, BlockInfo b){
//         return a.lastTime > b.lastTime; //min heap
//     }
// };

class Cache
{
public: // need lock
    ByteMap<Block*> dataMap;
    void nameSeqToKey(char* buf, const char* name, IUINT32 index);

    
    Cache(int nameLen);
    int insert(const char* name, IUINT32 dataStart, IUINT32 dataEnd, const char* dataBuf);
    int read(const char* name, IUINT32 dataStart, IUINT32 dataEnd, char* dataBuf);
private: // doesn't need lock
    int KeyLen;
    // priority_queue<BlockInfo, vector<BlockInfo>, cmp> queueLRU;
    list<Node> lruList;
    // key = name + blockStart
    // KeyLen = name + sizeof(IUNIT32)
    mutex lock;
    Block* addBlock(const char* key);
    void dropBlock(list<Node>::iterator iter);
    void updateLRU(Block* blockPtr);
    int checksum(const char* keyChars);
};


#endif