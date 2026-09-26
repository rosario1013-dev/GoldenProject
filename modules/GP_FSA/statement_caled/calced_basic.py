from GP_FSA import Caled


# Equaty의 위험수준별구조를 위한 계산
Caled('BPS').En('BPS').Formula("PS(归属于母公司股东权益总计)")
Caled('BPS_low').Formula("PS(归属于母公司股东权益总计 - 商誉 - 无形资产)")
Caled('BPS_low_low').Formula("PS(归属于母公司股东权益总计 - 商誉 - 无形资产 - 长期股权投资)")





Caled('BPS加5年净利润').En('BPS_5NetProfit').Formula("FQ((S5(Ki(归属于母公司股东的净利润)) + 归属于母公司股东权益总计 + 库存股)/总股本)")
Caled('BPS去除商誉').En('BPS_no_goodwill').Formula("FQ((归属于母公司股东权益总计 + 库存股 - 商誉) /总股本)")
Caled('BPS加5年自由现金流').En('BPS_5FC').Formula("FQ((S5(Ki(自由现金流)) + 归属于母公司股东权益总计)/总股本)")
Caled('每股基本营业收入').En('').Formula("FQ(S5(Ki(营业总收入))/总股本)")
Caled('每股基本营业成本').En('').Formula("FQ(S5(Ki(营业成本))/总股本)")



Caled('Op_Revenue').Formula("Ki(营业总收入_营业收入)")

Caled('EPS').En('EPS').Formula("PS(Ki(归属于母公司股东的净利润))")