import socket
from datetime import datetime 
import time 
import argparse

# 1.创建socket

tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

parser = argparse.ArgumentParser()
parser.add_argument("-c",type=int,default=100,help="test packets numbers")
parser.add_argument("-rt",type=int,default=200,help="rtt total")

args = parser.parse_args()

# 2. 链接服务器
server_addr = ("10.0.2.1", 3000)
tcp_socket.connect(server_addr)

# 3. 发送数据
for i in range(args.c):
    curTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    #print(curTime)
    send_data = curTime
    tcp_socket.send(send_data.encode("gbk"))
    
    recv_data = tcp_socket.recv(1024)
    recvTime = datetime.now()
    sendTime = datetime.strptime(recv_data.decode('gbk'),'%Y-%m-%d %H:%M:%S.%f')
    deltaTime = 1000*((recvTime-sendTime).total_seconds())
    
    print('recvTime:',recvTime.strftime('%Y-%m-%d %H:%M:%S.%f'),end="  ")
    print('sendTime:', recv_data.decode('gbk'),end="  ")
    print('rtt:%fms'%(deltaTime))
    #time.sleep(1)
    
# 4. 关闭套接字
tcp_socket.close()
