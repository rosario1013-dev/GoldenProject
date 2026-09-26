from GP_FSA import tables
from GP_FSA.core.table import Table
from GP_FSA import accounts, Caled

# Caled('EBIT').Formula(
#     "营业总收入_营业收入"
#     " - 营业成本"
#     " - 销售费用"
#     " - 管理费用"
#     " - 研发费用_IS"
#     " - 勘探费用"
#     " - 营业税金及附加"
# )
# Caled('YEBIT').Formula("Ki(EBIT)")
# # Caled('YEBIT_PS').Formula("FQ(S5(YEBIT) + 归属于母公司股东权益总计 + 库存股/总股本)")
# Caled('YEBIT_PS').Formula("FQ((S5(Ki(EBIT)) + 归属于母公司股东权益总计 + 库存股)/总股本)")


tables['assign_EBIT'] = Table().Item([
    accounts['营业总收入_营业收入'].copy().tag_level(1),
        accounts['营业成本'].copy().tag_level(1),
        accounts['销售费用'].copy().tag_level(1),
        accounts['管理费用'].copy().tag_level(1),
        accounts['研发费用_IS'].copy().tag_level(1),
        accounts['勘探费用'].copy().tag_level(1),
        accounts['营业税金及附加'].copy().tag_level(1),
    accounts['EBIT'].copy().tag_level(1).Color('red'),
    accounts['营业利润'].copy().tag_level(1).Color('green'),
    accounts['息税前利润_EBIT'].copy().tag_level(1).Color('green'),
])
