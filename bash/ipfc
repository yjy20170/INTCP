#!/bin/bash
cd `dirname $0`
# start iperf client
# server is at 10.0.$1
# sending duration is $2

[ -r ../my.conf ] && . ../my.conf
if [ -n "$2" ] ;then
  iperf -c 10.0.$1 -p 5001 -i 1 -t $2 -w ${IPERF_WIN} # -l 1000K
else
  iperf -c 10.0.$1 -p 5001 -i 1 -t 10
fi
