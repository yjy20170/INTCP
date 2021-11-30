#!/bin/bash
cd `dirname $0`
# set iptables

# clear existing rules
sudo iptables -t mangle -F

# set configuration-based route
ip rule add fwmark 1 table 100 
ip route add local 0.0.0.0/0 dev lo table 100

# filter the local network packets
iptables -t mangle -N MID
iptables -t mangle -A MID -d 127.0.0.1/32 -j RETURN
iptables -t mangle -A MID -d 224.0.0.0/4 -j RETURN 
iptables -t mangle -A MID -d 255.255.255.255/32 -j RETURN 

# mark UDP packets tag "1"， forward to given port
# iptables -t mangle -A MID -p ${PROTOCOL} -j TPROXY --on-port ${MID_PORT} --tproxy-mark 1 
iptables -t mangle -A MID -p UDP -j TPROXY --on-port $1 --tproxy-mark 1
iptables -t mangle -I MID -m mark --mark 0xff -j RETURN # avoid infinite loop

# make the configuration effective
iptables -t mangle -A PREROUTING -j MID
