#!/usr/bin/python
#coding=utf-8

import NetHelper
import automnArgs


if __name__=="__main__":

    for args in automnArgs.argsSet:
       NetHelper.mngo(args)
    
    os.system("killall -9 automn >/dev/null 2>&1")
