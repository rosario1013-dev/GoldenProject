from GP_FSA import Caled

Caled('净资产收益率_1Y').En('ROE_1Y').Formula("Ki(归属于母公司综合收益)/Fi(归属于母公司股东权益总计)")
Caled('总资产收益率_1Y').En('ROA_1Y').Formula("Ki(综合收益总额)/Fi(负债和股东权益合计)")
Caled('归母净利润同比_1Y').En('GMJLR_TB_1Y').Formula("YDif(Ki(归属于母公司综合收益)) / Ki(归属于母公司综合收益)")
Caled('归母净利润同比').En('GMJLR_TB').Formula("Dif(归属于母公司综合收益) / Pre(归属于母公司综合收益)")
Caled('营业总收入同比_1Y').En('GMJLR_TB_1Y').Formula("YDif(Ki(营业总收入_营业收入)) / Ki(营业总收入_营业收入)")
Caled('营业总收入同比').En('GMJLR_TB').Formula("Dif(营业总收入_营业收入) / Pre(营业总收入_营业收入)")
Caled('营业总收入_单季同比').En('YYZSR_TB').Formula("Dif(营业总收入_营业收入) / Pre(营业总收入_营业收入)")
Caled('每股流动资产').En('CA_PS').Formula("流动资产合计/总股本")
Caled('FQ每股流动资产').En('CA_PS').Formula("FQ(流动资产合计/总股本)")
Caled('FQ每股净流动资产').En('FQ_NCA_PS').Formula("FQ((流动资产合计-流动负债合计)/总股本)")
Caled('PKV').En('PKV').Formula("getPKV()")
Caled('毛利率').En('EBIT').Formula("营业利润 / 营业总收入_营业收入")

Caled('管理费用比例').Formula("Ki(管理费用)/Ki(营业总收入)*100")
Caled('销售费用比例').Formula("Ki(销售费用)/Ki(营业总收入)*100")
Caled('研发费用比例').Formula("Ki(研发费用_IS)/Ki(营业总收入)*100")
Caled('营业成本比例').Formula("Ki(营业成本)/Ki(营业总收入)*100")