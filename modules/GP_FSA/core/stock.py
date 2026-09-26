from GP_KDB import KDB
import math
log101 = math.log(1.01)

from GP_FSA import accounts
def logize(x):
    if x > 1:
        return math.log(x)/log101
    else:
        return 0


class Stock:
    
    def __init__(self, IDE):
        self.IDE = IDE

    def load_FS(self, endDT=None):
        if hasattr(self, 'FS'): return self
        self.FS = KDB().CW_STOCK(self.IDE)
        index = self.FS.index
        df = self.FS.join(KDB().FH(self.IDE).set_index('DT')['PKV'], how='outer')
        df['PKV'] = df['PKV'].ffill()
        df = df.ffill()
        df = df.bfill()
        self.FS = df.loc[index]
        self.PKV = self.FS['PKV']  
        return self

    def FQ(self, a):
        if not hasattr(self, 'PKV'): 
            raise Exception('Stock({}) has not PKV table.'.format(self.IDE))
        aa = a * self.PKV
        aa[aa<=0.001] = None
        return aa.apply(lambda x: logize(x))

    def getPKV(self):
        return self.PKV

    def iFQ(self, a):
        if 'PKV' not in self.FS.columns: return None
        b = a.apply(lambda x: math.exp(x * log101))
        return b / self.FS['PKV']

    def PS(self, a):
        if not hasattr(self, 'PKV'):
            raise Exception('Stock({}) has not PKV table.'.format(self.IDE))
        return self.FQ(a/accounts['总股本'].value(self))