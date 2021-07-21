import socket
from datetime import datetime
import argparse
# 创建socket
tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 本地信息
#address = ('', 7788)
address = ('',3000)
# 绑定
tcp_server_socket.bind(address)

# 使用socket创建的套接字默认的属性是主动的，
# 使用listen将其变为被动的，这样就可以接收别人的链接了
tcp_server_socket.listen(128)


tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

parser = argparse.ArgumentParser()
parser.add_argument("-c",type=int,default=100,help="test packets numbers")
parser.add_argument("-rt",type=int,default=200,help="rtt total")

args = parser.parse_args()
print("test packets number:",args.c)
print("rtt total:",args.rt)

# 如果有新的客户端来链接服务器，
# 那么就产生一个新的套接字专门为这个客户端服务
# client_socket用来为这个客户端服务
# tcp_server_socket就可以省下来专门等待其他新客户端的链接
client_socket, clientAddr = tcp_server_socket.accept()
cnt = 0
# 接收对方发送过来的数据
#for i in range(args.c):
while True:
    #recv_data = client_socket.recv(1024)  # 接收1024个字节
    recv_data = client_socket.recv(26)  # 接收1024个字节
    recvTime = datetime.now()
    sendTime = datetime.strptime(recv_data.decode('gbk'),'%Y-%m-%d %H:%M:%S.%f')
    deltaTime = 1000*((recvTime-sendTime).total_seconds())
    #client_socket.send(recv_data)
    cnt += 1
    print("len=",len(recv_data))
    print("packet %3d"%cnt,end="  ")
    print('recvTime:',recvTime.strftime('%Y-%m-%d %H:%M:%S.%f'),end="  ")
    print('sendTime:', recv_data.decode('gbk'),end="  ")
    print('deltaTime:%fms'%(deltaTime),flush=True)
client_socket.close()
