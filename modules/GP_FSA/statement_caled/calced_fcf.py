from GP_FSA import Caled

Caled('投入减少资本_少数').Formula("YDif(少数股东权益_EQ) - 归属于少数股东综合收益 + 子公司支付给少数股东的股利利润")
Caled('投入减少资本').Formula("YDif(实收资本) + YDif(其他权益工具_EQ) + YDif(资本公积) - YDif(库存股) + 投入减少资本_少数")
Caled('股利').Formula("综合收益总额 - YDif(股东权益合计) + 投入减少资本")
Caled('利息').Formula("分配股利利润或偿付利息支付的现金 - 股利")


formula_自由现金流 = ''
formula_自由现金流 += '经营活动现金流入小计'
formula_自由现金流 += ''
formula_自由现金流 += ' - 购建固定资产无形资产和其他长期资产支付的现金'
formula_自由现金流 += ' + 取得子公司及其他营业单位支付的现金净额'
formula_自由现金流 += ' + 处置固定资产无形资产和其他长期资产收回的现金净额'
formula_自由现金流 += ' + 处置子公司及其他营业单位收到的现金净额'
formula_自由现金流 += ' + 取得借款收到的现金'
formula_自由现金流 += ' - 分配股利利润或偿付利息支付的现金'
formula_自由现金流 += ' + 股利'
formula_自由现金流 += ''
formula_自由现金流 += ''
formula_自由现金流 += ' + 子公司吸收少数股东投资收到的现金'

Caled('自由现金流').Formula(formula_自由现金流)

Caled('不属于现金及现金等价物的货币资金').Formula("货币资金-期末现金及现金等价物余额")
