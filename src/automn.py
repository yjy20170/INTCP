#!/usr/bin/python
#coding=utf-8

import NetHelper
import automnArgs
from tqdm import tqdm

if __name__=="__main__":

    for args in tqdm(automnArgs.argsSet):
        NetHelper.mngo(args)
    
    os.system("killall -9 automn >/dev/null 2>&1")
