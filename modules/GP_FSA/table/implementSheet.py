from GP_FSA.core.table import Table
from GP_FSA import accounts

tbl_CSimp = Table()
tbl_CSimp.Item([
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
        # ---------------------
        accounts['债务转为资本'].copy().tag_level(1).Color('red'),
        accounts['一年内到期的可转换公司债券'].copy().tag_level(1).Color('red'),
        accounts['融资租入固定资产'].copy().tag_level(1).Color('red'),

        accounts['现金的期末余额'].copy().tag_level(1),
        accounts['现金的期初余额'].copy().tag_level(1).Color('red').U(-1),

        accounts['现金等价物的期末余额'].copy().tag_level(1),
        accounts['现金等价物的期初余额'].copy().tag_level(1).Color('red').U(-1),

    accounts['现金及现金等价物净增加额'].copy().Color('#e5e7eb'), 

])

