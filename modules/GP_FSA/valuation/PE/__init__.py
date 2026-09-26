import math
log101 = math.log(1.01)

def logize(x):
    if x > 1:
        return math.log(x)/log101
    else:
        return 0

def func_logize(func):
    def wrapper(*args, **kwargs):
        return logize(func(*args, **kwargs))
    return wrapper

from GP_FSA.valuation.PE.FairPB_on_fixed_COE import FairPB as PB_from_fiexed_COE
from GP_FSA.valuation.PE.FairPB_on_fixed_COE import FairX_Realized_Required


