from io import BytesIO
from token import NAME
from tokenize import tokenize, untokenize

from GP_FSA import Acc, accounts
from GP_FSA.core.formula import *


class Caled(Acc):
    def __init__(self, ID):
        super().__init__(ID)
        accounts[self.ID] = self

    def __repr__(self):
        return f"➢【Formula】{self.ID}, 단위={self.unit}"

    def Formula(self, formula):
        self.formula_ori = formula
        result = []
        g = tokenize(BytesIO(formula.encode('utf-8')).readline)  # tokenize the string
        for toknum, tokval, _, _, _ in g:
            if toknum == NAME:
                if tokval in ['Ki', 'Bi', 'Kis', 'Qi', 'Fi', 'Pre', 'Dif', 'YDif', 'ColPlus', 'KLog', 'NotNeg', 'S5']:
                    result.append((toknum, tokval))
                elif tokval in ['PS', 'FQ', 'FQV', 'FQK', 'FS', 'iFQ', 'iFQ2', 'FQK', 'getPKV']:
                    result.extend([(NAME, "st." + tokval)])
                elif tokval in accounts:
                    result.extend([(NAME, f"accounts['{tokval}'].value(st)")])
                else:
                    result.extend([(NAME, tokval+".value(st)")])
            else:
                result.append((toknum, tokval))
        self.formula = untokenize(result).decode('utf-8')
        return self

    def value(self, st):
        if not hasattr(st, 'FS'):
            raise Exception('Stock({}) has not FS table.'.format(st.IDE))
        re = eval(self.formula)
        return re