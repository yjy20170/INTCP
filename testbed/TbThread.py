import threading
import time

NormalThreads = []
LatchThreads = []

def threadFunc(isLatchThread):
    prefix = 'Latch' if isLatchThread else 'Normal'
    def wrapper(func):
        def funcNew(*args, **kwargs):
            if not isLatchThread:
                time.sleep(0.1)
            print('[ %s Thread start ] %s' % (prefix,func.__name__))
            ret = func(*args, **kwargs)
            print('[ %s Thread  end  ] %s' % (prefix,func.__name__))
            return ret
        if isLatchThread:
            thread = LatchThread(funcNew)
            LatchThreads.append(thread)
        else:
            thread = NormalThread(funcNew)
            NormalThreads.append(thread)
        return thread
    return wrapper


class NormalThread:
    def __init__(self, func):
        self.func = func
        self.thread = None
    def start(self, *args, **kwargs):
        self.thread = threading.Thread(daemon=True, target=self.func, args=args, kwargs=kwargs)
        self.thread.start()
    def join(self):
        self.thread.join()


def LatchFunc(func):
    def funcNew(*args,**kwargs):
        LatchThread.incNum()
        ret = func(*args,**kwargs)
        LatchThread.decNum()
        return ret
    return funcNew
class LatchThread(NormalThread):
    Num = 0
    def __init__(self, func):
        super().__init__(LatchFunc(func))
    def start(self, *args, **kwargs):
        self.thread = threading.Thread(daemon=False, target=self.func, args=args, kwargs=kwargs)
        super().start(*args,**kwargs)
    @classmethod
    def running(cls):
        return cls.Num > 0
    @classmethod
    def incNum(cls):
        cls.Num += 1
    @classmethod
    def decNum(cls):
        cls.Num -= 1


def smartRun(threads, *args, **kwargs):
    latchThreads = []
    normalThreads = []
    for thrd in threads:
        if thrd.__class__ == LatchThread:
            latchThreads.append(thrd)
        else:
            normalThreads.append(thrd)
    for thrd in latchThreads:
        thrd.start(*args,**kwargs)
    for thrd in normalThreads:
        thrd.start(*args,**kwargs)
    # normal threads keep running until latchThread ends

def waitLatch(threads):
    latchThreads = []
    for thrd in threads:
        if thrd.__class__ == LatchThread:
            latchThreads.append(thrd)
    # for thread in normalThreads+latchThreads:
    #NOTE do not wait normalThreads now
    for thread in latchThreads:
        thread.join()



atomicLock = threading.Lock()
def atomic(func):
    def wrapper(*args, **kwargs):
        atomicLock.acquire()
        ret = func(*args, **kwargs)
        atomicLock.release()
        return ret
    return wrapper
