#!/bin/bash
cd `dirname $0`
INTCP="../../intcp"
echo "start making..."
g++ -c ${INTCP}/*.cpp -lpthread -g
echo "making intcps"
g++ intcp_server.cpp *.o -o intcps -lpthread -g
echo "making intcpm"
g++ intcp_mid.cpp    *.o -o intcpm -lpthread -g
echo "making intcpc"
g++ intcp_client.cpp *.o -o intcpc -lpthread -g
echo "finished."
rm *.o

# -g is for gdb
# https://blog.csdn.net/qq_41006901/article/details/90699486