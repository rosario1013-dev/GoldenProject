import math
from . import logize

COE = 0.085
Doubler = math.log(((math.exp(COE)-1)*2)+1)

def FairPB(ROE):
    return max((Doubler - 2*COE +ROE)/(Doubler-COE), 0.5)

def logFairPB(ROE):
    return logize(FairPB(ROE))

def FairX_Realized_Required(realized, required):
    Doubler = math.log(((math.exp(required) - 1) * 2) + 1)
    return max((Doubler - 2*COE +realized)/(Doubler-required), 0.5)