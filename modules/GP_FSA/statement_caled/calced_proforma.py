from GP_FSA import Caled

formula_ST_Debt = '短期借款  + 吸收存款及同业存放 + 向中央银行借款'
formula_ST_Debt += ' + 拆入资金 + 交易性金融负债 + 衍生金融负债'
Caled('ST_Debt').Formula(formula_ST_Debt)

formula = '长期借款 + 应付债券 + 租赁负债'
Caled('LT_Debt').Formula(formula)

formula = 'ST_Debt + LT_Debt + 少数股东权益_EQ + 一年内到期的非流动负债'
Caled('Financing_Obli').Formula(formula)

Caled('复权的每股金融负债').En('FinObli_PS').Formula("FQ(Financing_Obli/总股本)")
Caled('复权的每股总资产').En('Equ_PS').Formula("FQ(负债和股东权益合计/总股本)")

Caled('复权的每股流动资产').En('CA_PS').Formula("FQ(流动资产合计/总股本)")
Caled('股东权益加五年净利润').Formula("S5(Ki(归属于母公司股东的净利润)) + 归属于母公司股东权益总计 + 库存股")




# 行业分析



