import math
def convert(w):
    try:
        return float(w)
    except:
        return w

levelDict = {'+':1,'-':1,'*':2,'/':2,'^':3}
singleOps = ['-', '$','L']
def do(x,op,y):
    if op=='/' and y==0:
        raise Exception('division by zero')
    return x+y if op=='+' else x-y if op=='-' else x*y if op=='*' else x/y if op=='/' else x**y
def doSingle(x,op):
    return -1*x if op=='-' else x**0.5 if op=='$' else math.log(x)

tokens = []
def eat(level=-1):
    global tokens
    if len(tokens)==0 or type(tokens[-1])==str:
        raise Exception('input incomplete')
    curNum=tokens.pop()
    while (len(tokens)==1 or (len(tokens)>1 and type(tokens[-2])==str)) and tokens[-1] in singleOps:
        curNum = doSingle(curNum,tokens.pop())
    if len(tokens)==0 or levelDict[tokens[-1]]<level:
        return curNum
    else:
        curOp = tokens.pop()
        tokens.append(do(eat(levelDict[curOp]),curOp,curNum))
        return eat(level)

def calc(string):
    global tokens
    for char in string:
        if char not in '1234567890. '+''.join(list(levelDict.keys()) + singleOps):
            raise Exception('illegal symbol')
    for key in list(levelDict.keys()) + singleOps:
        string = string.replace(key,' %s '%key)
    tokens = list(map(convert,string.strip().split()))
    return eat()

while 1:
    string=input()
    if string=='quit':
        break
    else:
        try:
            print('%.3f'%calc(string))
        except Exception as e:
            print(e)