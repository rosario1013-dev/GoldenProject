from GP_FSA.core.table import Table
from GP_FSA  import accounts

# tbl_Dashboard = Table()
# tbl_Dashboard.Item([
#     accounts['营业总收入'].copy().tag_level(1),
#     accounts['净利润'].copy().tag_level(1),
#     accounts['归属于母公司股东的净利润'].copy().tag_level(1),
#     accounts['销售商品提供劳务收到的现金'].copy().tag_level(1).tag_Name('销售商品、提供劳务收到的现金'),
#     accounts['期末现金及现金等价物余额'].copy().Color('#e5e7eb'),
#     accounts['净资产收益率'].copy().tag_level(1).Color('#e5e7eb').tag_Name('ROE'),
#     accounts['基本每股收益'].copy().tag_level(1).Color('#e5e7eb').tag_Name('Basic_BPS'),
#     accounts['营业收入增长率Tpct'].copy().tag_level(1).Color('#e5e7eb').tag_Name('营业收入增长率 %'),
#     accounts['净利润增长率Tpct'].copy().tag_level(1).Color('#e5e7eb').tag_Name('净利润增长率 %'),
#     accounts['营业利润增长率Tpct'].copy().tag_level(1).Color('#e5e7eb').tag_Name('营业利润增长率 %'),
# ])

tbl_Dashboard = Table()
tbl_Dashboard.Item([
    accounts['净资产收益率_1Y'].copy().tag_Name('ROE').Color('#e5e7eb').Percent(),
    accounts['总资产收益率_1Y'].copy().tag_Name('ROA').Color('#e5e7eb').Percent(),
    accounts['归母净利润同比'].copy().Color('#e5e7eb').Percent(),
    accounts['营业总收入同比'].copy().Color('#e5e7eb').Percent(),
    accounts['净资产比率'].copy().Color('#e5e7eb').Percent(),
    accounts['Net_Financing_Obli'].copy().Color('#e5e7eb'),
    accounts['Gearing Ratio'].copy().Color('#e5e7eb').Percent(),
])

tbl_COST = Table()
tbl_COST.Item([
    accounts['营业成本比例'].copy().Color('#e5e7eb').Percent(),
    accounts['管理费用比例'].copy().tag_Name('管理费用比例').Color('#e5e7eb').Percent(),
    accounts['销售费用比例'].copy().tag_Name('销售费用比例').Color('#e5e7eb').Percent(),
    accounts['研发费用比例'].copy().Color('#e5e7eb').Percent(),
])


tbl_Reformed_BS = Table()
tbl_Reformed_BS.Item([
    accounts['营业总收入'].copy().Color('#e5e7eb').tag_Name('一、营业总收入'), 
    accounts['营业总成本'].copy().Color('#e5e7eb').tag_Name('二、营业总成本'), 
    accounts['营业利润'].copy().Color('#e5e7eb').tag_Name('三、营业利润'), 
    accounts['利润总额'].copy().Color('#e5e7eb').tag_Name('四、利润总额'),
    accounts['净利润'].copy().Color('#e5e7eb').tag_Name('五、净利润'),
    accounts['归属于母公司股东的净利润'].copy().tag_Name('六. 归属于母公司股东的净利润'),
    accounts['综合收益总额'].copy().Color('#e5e7eb').tag_Name('七、综合收益总额'),
    accounts['流动资产合计'].copy().Color('#e5e7eb'),
    accounts['非流动资产合计'].copy().Color('#e5e7eb'),
    accounts['资产总计'].copy().Color('#e5e7eb'),
    accounts['流动负债合计'].copy().Color('#e5e7eb'),
    accounts['非流动负债合计'].copy().Color('#e5e7eb'),
    accounts['总股本'].copy().Color('#e5e7eb').copy(),
    accounts['未分配利润'].copy(),
    accounts['归属于母公司股东权益总计'].copy().Color('#e5e7eb'),
    accounts['少数股东权益_EQ'].copy().Color('#e5e7eb'),
    accounts['股东权益合计'].copy().Color('#e5e7eb'),
])

