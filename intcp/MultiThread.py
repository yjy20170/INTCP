#!/usr/bin/python
import time
import threading
    
class Thread (threading.Thread):

    def __init__(self, func, args=(), kwargs={}):
        threading.Thread.__init__(self)
        self.func=func
        self.args=args
        self.kwargs=kwargs
    def run(self):
        self.func(*self.args, **self.kwargs)
        
class ReleaserThread(Thread):
    Running = False
    def __init__(self, func, args=(), kwargs={}):
        super().__init__(func, args, kwargs)
        self.__class__.Running = True
    def waitToStop(self):
        self.join()
        self.__class__.Running = False
    @classmethod
    def isRunning(cls):
        return cls.Running
        
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
