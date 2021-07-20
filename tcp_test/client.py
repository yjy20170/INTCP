#!/usr/bin/python3

import socket
from threading import Thread
import time

import Utils


def sendFunc(tcp_socket):
    while 1:
        # 8 bytes
        strTime = Utils.getStrTime()
        # 1024 bytes in all
        strPadded = Utils.padStr(strTime, 1024)
        bytesToSend = strPadded.encode('utf8')
        Utils.sendData(tcp_socket.send, bytesToSend)

def recvFunc(tcp_socket):
    idxPkt = 0
    recv_data_generator = Utils.recvData(tcp_socket.recv)
    last = time.time()
    lastIdx = 0
    while 1:
        data = recv_data_generator.__next__()
        # print('idx', idxPkt, 'owd', Utils.timeDelta(data[8:16], data[0:8]),
        #       'rtt', Utils.timeDelta(Utils.getStrTime(), data[0:8]))
        if len(data) != 16:
            print(idxPkt, data)
            print()
        idxPkt += 1
        cur = time.time()
        if cur-last>=1:
            print((idxPkt-lastIdx)*8/1024,'Mbps')
            lastIdx = idxPkt
            last = cur

if __name__=='__main__':
    # create socket
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # server_addr = ("10.0.2.1", 3000)
    server_addr = ("127.0.0.1", 3000)
    tcp_socket.connect(server_addr)

    sendThread = Thread(target=sendFunc, args=(tcp_socket,))
    sendThread.start()
    recvThread = Thread(target=recvFunc, args=(tcp_socket,))
    recvThread.start()

    sendThread.join()
    recvThread.join()
    tcp_socket.close()
