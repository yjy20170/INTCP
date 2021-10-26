#!/usr/bin/python3

import socket
import Utils


        
if __name__=='__main__':
    tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print('socket created.')

    address = ('',3000)
    tcp_server_socket.bind(address)

    # the created socket is positive by default.
    # use listen() to make it negative, so that it can listen to others' positive socket
    tcp_server_socket.listen(128)

    print('wait for client...')
    # a new socket only for one client will be created.
    client_socket, clientAddr = tcp_server_socket.accept()
    client_socket.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)

    recv_data_generator = Utils.recvData(client_socket.recv)
    idxPkt=0
    while(1):
        data = recv_data_generator.__next__()
        strTime = Utils.getStrTime()
        idxPkt+=1
        print('idx', idxPkt, 'sendTime',data[0:8],'curTime', strTime,'owd_obs',Utils.timeDelta(strTime,data[0:8]),flush=True)
        
        # 24 bytes in all
        # strPadded = Utils.padStr(data + strTime, 26)
        # bytesToSend = strPadded.encode('utf8')
        #Utils.sendData(client_socket.send, bytesToSend)


    client_socket.close()

