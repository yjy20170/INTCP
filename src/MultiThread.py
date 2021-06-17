#!/usr/bin/python
import time
import threading
    
class Thread (threading.Thread):
    Stopped = False

    def __init__(self, func, args=(), kwargs={}):
        threading.Thread.__init__(self)
        self.func=func
        self.args=args
        self.kwargs=kwargs
    def run(self):
        self.func(*self.args, **self.kwargs)
    def waitToStop(self):
        self.join()
        Thread.Stopped = True
    @classmethod
    def stopped(cls):
        return cls.Stopped
atomicLock = threading.Lock()
def atomic(func):
    def wrapper(*args, **kwargs):
        #cur=time.time()
        atomicLock.acquire()
        #print(time.time()-cur)
        ret = func(*args, **kwargs)
        atomicLock.release()
        return ret
    return wrapper
