import datetime
print(type(datetime.datetime.now()))
curTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
t = datetime.datetime.strptime(curTime,'%Y-%m-%d %H:%M:%S.%f')
print(type(t))
print(t)
print(type(curTime))
print(curTime)
