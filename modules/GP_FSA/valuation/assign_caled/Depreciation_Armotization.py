from GP_FSA import tables
from GP_FSA.core.table import Table
from GP_FSA import accounts, Caled
from GP_FSA import statement_caled



Caled('YEBITDA_PS').Formula("FQ((S5(Ki(EBITDA)) + 归属于母公司股东权益总计 + 库存股)/总股本)")



tables['assign_EBITDA'] = Table().Item([
    accounts['固定资产折旧油气资产折耗生产性生物资产折旧'].copy().tag_level(1),
    accounts['投资性房地产的折旧及摊销'].copy().tag_level(1),
    accounts['使用权资产折旧'].copy().tag_level(1),
    accounts['无形资产摊销'].copy().tag_level(1),
    accounts['信用减值损失'].copy().tag_level(1),
    accounts['DA'].copy().tag_level(1).Color('red'),
    accounts['EBITDA'].copy().tag_level(1).Color('red'),
    accounts['息税折旧摊销前利润_EBITDA'].copy().tag_level(1).Color('green'),
])