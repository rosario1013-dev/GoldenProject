from . import loginaztion



# 1년간류동고 = (현잔고) + (년초잔고-1년전잔고) = (현잔고-1년전잔고) + (년초잔고)
def Ki(a):
    b = a.copy()
    for d in list(a.index):
        b[d] = None
        yy = str(int(d[:4])-1)+'-12-31'
        if yy in a.index:   b[d] = a[yy]
    return a - a.shift(4) + b

def Bi(a):
    b = a.shift(4)
    return (a - b) / b


def S5(a):
    discount = 1.1
    s = 0
    for i in range(5):
        k = i + 1
        s += a/discount**k
    return s


def Kis(a, k = 2):
    kia = Ki(a)
    re = kia.copy()
    for i in range(k-1):
        re += kia.shift(4 + 4*i)
    return  re



def Qi(a):
    b = a - a.shift(1)
    for d in list(a.index):
        if d[4:] == '-03-31': b[d] = a[d]
    return b



def Fi(a):
    return (a.shift(4) + a)/2



def Pre(a):
    return a.shift(4)



def Dif(a):
    return a - a.shift(4)



def YDif(a):
    b = a.copy()
    for d in list(a.index):
        b[d] = None; yy = str(int(d[:4])-1)+'-12-31'
        if yy in a.index:   b[d] = a[yy]
    return a - b



def ColPlus(dt, a):
    re = dt.copy()
    for c in re.columns: re[c] = re[c] + a
    return re



def KLog(a):
    return a.apply(loginaztion)



def NotNeg(a):
    b = a.copy()
    b[b<0] = 0
    return b

