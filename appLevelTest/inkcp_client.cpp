#include "../pepsalUDP/src/ikcp.c"
#include <stdio.h>
#include <iostream>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <unistd.h>

using namespace std;

const int maxBufSize = 500;

struct UdpOutObj{
    int send_fd;
    struct sockaddr_in* recv_addr;
    char udpBuff[maxBufSize];
    
    UdpOutObj(int _send_fd,struct sockaddr_in* _recv_addr):send_fd(_send_fd),recv_addr(_recv_addr){}
    int recv_udp(){
        int addrLen = sizeof(struct sockaddr_in);
        int recvBytes = recvfrom(send_fd,udpBuff,sizeof(udpBuff),MSG_DONTWAIT,(struct sockaddr*)recv_addr,(socklen_t*)&addrLen);
        return recvBytes;
    }
};

int udp_output(const char* buf,int len,ikcpcb* kcp,void* user){
    UdpOutObj* p = (UdpOutObj*)user;
    int sendbyte = sendto(p->send_fd,buf,len,0,(struct sockaddr *)(p->recv_addr),sizeof(struct sockaddr_in));
    return sendbyte;
}


void get_current_time(long *sec, long *usec)
{
	struct timeval time;
	gettimeofday(&time, NULL);
	if (sec) *sec = time.tv_sec;
	if (usec) *usec = time.tv_usec;
}


IUINT32 getMillisec(){
    long sec,usec;
    IINT64 res;
    get_current_time(&sec,&usec);
    res = ((IINT64)sec) * 1000 + (usec / 1000);
    return (IUINT32)(res & 0xfffffffful);
}

int main(){
    int client_fd;
    struct sockaddr_in server_addr;
    
    char kcpBuff[maxBufSize];
    char apply_data[20] = "abcde";
    
    int recvbytes;
    int idxPkt = 0;
    //create clientfd
	if((client_fd=socket(AF_INET,SOCK_DGRAM,0))<0){
	    printf("create socket fail\n");
	    return -1;
	}
	
	//set server addr    
	server_addr.sin_family = AF_INET;
	server_addr.sin_port = htons(8000);
	server_addr.sin_addr.s_addr = inet_addr("10.0.2.1");
    //server_addr.sin_addr.s_addr = inet_addr("127.0.0.1");
    
    //create kcp and bind udpoutput
    UdpOutObj client_udpout(client_fd,&server_addr);
    ikcpcb* client_kcp = ikcp_create(0x1,(void*)&client_udpout);
	ikcp_setoutput(client_kcp,udp_output); 
	
	//set kcp paramaters
	ikcp_nodelay(client_kcp,1, 10, 2, 1);
	ikcp_wndsize(client_kcp,10,128);
	ikcp_setmtu(client_kcp,20);
    
    
    
    while(1){
        //sprintf(apply_data,"pkt %d",idxPkt);
        if(idxPkt<10){
            ikcp_request(client_kcp,idxPkt,idxPkt+2);
            idxPkt +=2;
        }
            
        //ikcp_send(client_kcp,apply_data,strlen(apply_data));  //send application layer here
        ikcp_update(client_kcp,getMillisec());
        while(1){
            int peeksize = ikcp_peeksize(client_kcp);
            if(peeksize<=0){
                break;
            }
            recvbytes = ikcp_recv(client_kcp,kcpBuff,peeksize);
            if(recvbytes<=0)
                break;
            kcpBuff[recvbytes]='\n';
            printf("%s",kcpBuff);
        }
        recvbytes = client_udpout.recv_udp();
        if(recvbytes>0){
            ikcp_input(client_kcp,client_udpout.udpBuff,recvbytes);
        }
        //usleep(1000);
        sleep(1);
    }
    
	return 0;
}
