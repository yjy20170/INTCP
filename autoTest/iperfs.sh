#!/bin/bash
cd `dirname $0`
# start iperf server

[ -r ../my.conf ] && . ../my.conf

iperf -s -p 5001 -i 1 -w ${IPERF_WIN}  #-l 1000K