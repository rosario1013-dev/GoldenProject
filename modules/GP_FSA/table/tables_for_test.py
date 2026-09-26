from GP_FSA.core.table import Table
from GP_FSA import accounts, Caled

Caled('OpCash_Net').En('OpCash_Net').Formula(
    "净利润 + 资产减值准备 + " +
    "信用减值损失 + " +
    "固定资产折旧油气资产折耗生产性生物资产折旧 + 使用权资产折旧 + " +
    "投资性房地产的折旧及摊销 + 无形资产摊销 + 长期待摊费用摊销 + 处置固定资产无形资产和其他长期资产的损失 + " +
    "固定资产报废损失 + " +
    "公允价值变动损失 + " +
    "财务费用_BC + " +
    "投资损失 + " +
    "递延所得税资产减少 + 递延所得税负债增加  + " +
    "存货的减少 + 经营性应收项目的减少 + 经营性应付项目的增加 + 其他_BC"
)

Caled('d_OpCash_Net').En('ddd').Formula(
    "OpCash_Net - 经营活动产生的现金流量净额_BC"
)

tbl = Table()
tbl.Item([
    accounts['净利润'].copy().tag_level(1),
    accounts['资产减值准备'].copy().tag_level(1),
    accounts['资产减值损失2019'].copy().tag_level(1).Color('green'),
    accounts['信用减值损失'].copy().tag_level(1),
    accounts['信用减值损失2019'].copy().tag_level(1).Color('green'),
    accounts['固定资产折旧油气资产折耗生产性生物资产折旧'].copy().tag_level(1).tag_Name('固定资产折旧、油气资产折耗、生产性生物资产折旧'),
    accounts['使用权资产折旧'].copy().tag_level(1),
    accounts['投资性房地产的折旧及摊销'].copy().tag_level(1),
    accounts['无形资产摊销'].copy().tag_level(1),
    accounts['长期待摊费用摊销'].copy().tag_level(1),
    accounts['处置固定资产无形资产和其他长期资产的损失'].copy().tag_level(1).tag_Name('处置固定资产、无形资产和其他长期资产的损失'),
    accounts['固定资产报废损失'].copy().tag_level(1),
    accounts['公允价值变动损失'].copy().tag_level(1),
    accounts['财务费用_BC'].copy().tag_level(1),
    accounts['投资损失'].copy().tag_level(1),
    accounts['递延所得税资产减少'].copy().tag_level(1),
    accounts['递延所得税负债增加'].copy().tag_level(1),
    accounts['存货的减少'].copy().tag_level(1),
    accounts['经营性应收项目的减少'].copy().tag_level(1),
    accounts['经营性应付项目的增加'].copy().tag_level(1),
    accounts['其他_BC'].copy().tag_level(1).tag_Name('其他'),
    accounts['经营活动产生的现金流量净额_BC'].copy().Color('#e5e7eb'),
    accounts['OpCash_Net'].copy().Color('red'),
    accounts['d_OpCash_Net'].copy(),
])

Caled('PD_EBIT').En('OpCash_Net').Formula("利润总额 + 财务费用_IS")
Caled('d_PD_EBIT').Formula("PD_EBIT - 息税前利润_EBIT")
tbl_EBIT = Table()
tbl_EBIT.Item([
    accounts['利润总额'].copy().tag_level(1),
    # accounts['其他收益_IS'].copy().tag_level(1).Color('red'),
    accounts['财务费用_IS'].copy().tag_level(1),
    accounts['PD_EBIT'].copy().Color('red').tag_level(1),
    accounts['息税前利润_EBIT'].copy().Color('red').tag_level(1),
    accounts['d_PD_EBIT'].copy().tag_level(1),
])




Caled('ppp').Formula(
    "营业总收入_营业收入 - 营业成本 - 营业税金及附加 -销售费用 - 管理费用 - 研发费用_IS - 勘探费用"
    # # # "- 财务费用_IS "
    # # " + 财务费用_利息费用 - 财务费用_IS "
    # "+ 其他收益_IS - 投资损失"
    # "- 资产减值损失 + 资产减值损失2019 - 信用减值损失"
    # " + 资产处置收益_IS"
)
tbl_profit = Table()
tbl_profit.Item([
    accounts['营业总收入_营业收入'].copy().tag_level(1),
    accounts['营业成本'].copy().tag_level(1),
    accounts['营业税金及附加'].copy().tag_level(1),

    accounts['销售费用'].copy().tag_level(1),
    accounts['管理费用'].copy().tag_level(1),
    accounts['研发费用_IS'].copy().tag_level(1),
    accounts['勘探费用'].copy().tag_level(1),
    accounts['财务费用_IS'].copy().tag_level(1).Color('red'),

    accounts['其他收益_IS'].copy().tag_level(1),
    accounts['投资损失'].copy().tag_level(1),
    accounts['公允价值变动损失'].copy().tag_level(1),
    accounts['资产减值损失'].copy().tag_level(1),
    accounts['资产减值损失2019'].copy().tag_level(1),


    accounts['信用减值损失'].copy().tag_level(1),
    # accounts['信用减值损失2019'].copy().tag_level(1),

    accounts['资产处置收益_IS'].copy().tag_level(1),

    accounts['财务费用_利息费用'].copy().tag_level(1).Color('red'),
    accounts['营业总收入_利息收入'].copy().tag_level(1).Color('red'),
    accounts['ppp'].copy().tag_level(1),
])

# ('资产减值准备', 'col135'),
# ('长期待摊费用摊销', 'col138'),
# # 待摊费用的减少_补充
# # 预提费用的增加_补充
# ('固定资产报废损失', 'col140'),
# ('公允价值变动损失', 'col141'),



Caled('DA').Formula(
    " + 固定资产折旧油气资产折耗生产性生物资产折旧"
    " + 投资性房地产的折旧及摊销"
    " + 使用权资产折旧"
    " + 无形资产摊销"
    " + 信用减值损失"

)
Caled('PD_EBITDA').Formula(
    " + ppp"
    " + da"
)
tbl_da = Table()
tbl_da.Item([
    accounts['固定资产折旧油气资产折耗生产性生物资产折旧'].copy().tag_level(1),
    accounts['投资性房地产的折旧及摊销'].copy().tag_level(1),
    accounts['使用权资产折旧'].copy().tag_level(1),
    accounts['无形资产摊销'].copy().tag_level(1),
    accounts['信用减值损失'].copy().tag_level(1),
    accounts['资产减值准备'].copy().tag_level(1),



    accounts['da'].copy().tag_level(1).Color('red'),
    accounts['PD_EBITDA'].copy().tag_level(1).Color('red'),

])