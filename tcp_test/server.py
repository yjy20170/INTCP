import socket
from datetime import datetime
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

# 如果有新的客户端来链接服务器，
# 那么就产生一个新的套接字专门为这个客户端服务
# client_socket用来为这个客户端服务
# tcp_server_socket就可以省下来专门等待其他新客户端的链接
client_socket, clientAddr = tcp_server_socket.accept()

# 接收对方发送过来的数据
while(1):
    recv_data = client_socket.recv(1024)  # 接收1024个字节
    recvTime = datetime.now()
    sendTime = datetime.strptime(recv_data.decode('gbk'),'%Y-%m-%d %H:%M:%S.%f')
    deltaTime = 1000*((recvTime-sendTime).total_seconds())
    client_socket.send(recv_data)
    print('recvTime:',recvTime.strftime('%Y-%m-%d %H:%M:%S.%f'),end="  ")
    print('sendTime:', recv_data.decode('gbk'),end="  ")
    print('deltaTime:%fms'%(deltaTime))
client_socket.close()
