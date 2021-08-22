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
    int server_fd;
    int recvbytes;
    int reusable = 1;
    int addrLen = sizeof(struct sockaddr_in);
    int idxPkt = 0;
    
    struct sockaddr_in server_addr;
    struct sockaddr_in client_addr;
    
    char kcpBuff[maxBufSize];
    char apply_data[20];
    
    //create serverfd
    if((server_fd=socket(AF_INET,SOCK_DGRAM,0))<0){
	    printf("create socket fail\n");
	    return -1;
	}
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &reusable, sizeof(int));
    
    //bind server addr
    server_addr.sin_family = AF_INET;
	server_addr.sin_port = htons(8000);
    server_addr.sin_addr.s_addr = INADDR_ANY;
    
    if(bind(server_fd, (struct sockaddr *)&server_addr, sizeof(struct sockaddr)) == -1){
		printf("bind fail\n");
		return -1;
    }
    
    //create kcp and bind udpoutput
    UdpOutObj server_udpout(server_fd,&client_addr);
    ikcpcb* server_kcp = ikcp_create(0x1,(void*)&server_udpout);
	ikcp_setoutput(server_kcp,udp_output); 
	
	//set kcp paramaters
	ikcp_nodelay(server_kcp,1, 10, 2, 1);
	ikcp_wndsize(server_kcp,10,128);
	ikcp_setmtu(server_kcp,20);
    
    for(idxPkt=0;idxPkt<10;idxPkt++){
        sprintf(apply_data,"pkt %d",idxPkt);
        ikcp_send(server_kcp,apply_data,strlen(apply_data));
    }
    
    while(1){
        while(1){
            int peeksize = ikcp_peeksize(server_kcp);
            if(peeksize<=0){
                break;
            }
            recvbytes = ikcp_recv(server_kcp,kcpBuff,peeksize);
            if(recvbytes<=0)
                break;
            kcpBuff[recvbytes]='\n';
            printf("%s",kcpBuff);
            //ikcp_send(server_kcp,kcpBuff,strlen(kcpBuff));
            //printf("%s %u",inet_ntoa(client_addr.sin_addr),ntohs(client_addr.sin_port));
        }
        recvbytes = server_udpout.recv_udp();
        if(recvbytes>0){
            ikcp_input(server_kcp,server_udpout.udpBuff,recvbytes);
        }
        //printf("here\n");
        ikcp_update(server_kcp,getMillisec());
        //usleep(1000);
        sleep(1);
    }
    return 0;
}
