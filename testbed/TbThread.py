import threading

class NormalThread:# (threading.Thread):
    
    def __init__(self, func, name='xxx'):
        # threading.Thread.__init__(self)
        self.func = func
        self.fname = name
        self.thread = None
    def start(self, args=(), kwargs={}):
        self.thread = threading.Thread(target=self.func, args=args, kwargs=kwargs)
        self.thread.start()
    def join(self):
        self.thread.join()
        self.thread = None
    #     self.args=args
    #     self.kwargs=kwargs
    #     super().start()
    # def run(self):
    #     self.func(*self.args, **self.kwargs)

    # def func(self, *args, **kwargs):
    #     return

        
class LatchThread(NormalThread):
    Running = 0
    def __init__(self, func, name='xxx'):

        def latchWrapper(func):
            def wrapped(*args, **kwargs):
                self.__class__.Running += 1
                func(*args, **kwargs)
                self.__class__.Running -= 1
            return wrapped

        super().__init__(latchWrapper(func), name)
        
    @classmethod
    def isRunning(cls):
        return cls.Running > 0
    @classmethod
    def pretendRunning(cls):
        cls.Running = 1
    @classmethod
    def resetRunning(cls):
        cls.Running = 0

def clear():
    LatchThread.resetRunning()

def smartStart(threads, args=(), kwargs={}):
    latchThrds = []
    normalThrds = []
    for thrd in threads:
        if thrd.__class__ == LatchThread:
            latchThrds.append(thrd)
        else:
            normalThrds.append(thrd)
    #print(len(latchThrds))
    if latchThrds == []:
        LatchThread.pretendRunning()
    for thrd in latchThrds:
        thrd.start(args,kwargs)
    for thrd in normalThrds:
        thrd.start(args,kwargs)

atomicLock = threading.Lock()
def atomic(func):
    def wrapper(*args, **kwargs):
        atomicLock.acquire()
        ret = func(*args, **kwargs)
        atomicLock.release()
        return ret
    return wrapper
