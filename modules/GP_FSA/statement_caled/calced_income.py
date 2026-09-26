from GP_FSA import Caled
# from GP_FSA.valuation import *

Caled('DA').Formula(
    " + 固定资产折旧油气资产折耗生产性生物资产折旧"
    " + 投资性房地产的折旧及摊销"
    " + 使用权资产折旧"
    " + 无形资产摊销"
    " + 信用减值损失"
)

Caled('EBIT').Formula(
    "营业总收入_营业收入"
    " - 营业成本"
    " - 销售费用"
    " - 管理费用"
    " - 研发费用_IS"
    " - 勘探费用"
    " - 营业税金及附加"
)

Caled('YEBIT').Formula("Ki(EBIT)")
Caled('YEBIT_PS').Formula("FQ((S5(Ki(EBIT)) + 归属于母公司股东权益总计 + 库存股)/总股本)")

Caled('EBITDA').Formula("EBIT + DA")
Caled('YEBITDA').Formula("Ki(EBITDA)")

Caled('Op_Revenue').Formula("Ki(营业总收入_营业收入)")
Caled('Op_Cost').Formula("Ki(营业成本)")
Caled('Op_fixed_Cost').Formula("Ki(营业成本) + Ki(营业税金及附加) + Ki(销售费用) + Ki(管理费用) + Ki(研发费用_IS) + Ki(勘探费用)")
Caled('Op_fixed_Cost_without_DA').Formula("Op_fixed_Cost - Ki(DA)")


Caled('Op_NetCashflow').Formula("Ki(经营活动产生的现金流量净额)")


Caled('Op_EBITDA_revenue').Formula("YEBITDA/Ki(营业总收入_营业收入)")
