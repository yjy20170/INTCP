#!/usr/bin/python
#coding=utf-8
from Args import Args
import NetHelper
from automnArgs import *
import os

NetHelper.mngo(argsSet[0],False)
print("all experiments finished")
os.system("killall -9 automn >/dev/null 2>&1")
