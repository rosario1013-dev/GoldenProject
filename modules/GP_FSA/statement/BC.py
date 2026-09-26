from GP_FSA import accounts
from GP_FSA.core.account import Regist_this_to_account_list


BC1 = ('经营活动产生的现金流量净额_BC',  'col150', [
    ('净利润', 'col134'),
    ('资产减值准备', 'col135'),
    (accounts['信用减值损失2019'], -1),
    ('固定资产折旧油气资产折耗生产性生物资产折旧', 'col136'),
    ('投资性房地产的折旧及摊销', 'col579', 10000),
    ('无形资产摊销', 'col137'),
    ('使用权资产折旧', 'col581', 10000),
    ('长期待摊费用摊销', 'col138'),
    # 递延收益摊销_补充
    # 待摊费用的减少_补充
    # 预提费用的增加_补充
    ('处置固定资产无形资产和其他长期资产的损失', 'col139'),
    ('固定资产报废损失', 'col140'),
    ('公允价值变动损失', 'col141'),
    ('财务费用_BC', 'col142'),
    ('投资损失', 'col143'),
    ('递延所得税资产减少', 'col144'),
    ('递延所得税负债增加', 'col145'),
    # 预计负债的增加_补充
    ('存货的减少', 'col146'),
    ('经营性应收项目的减少', 'col147'),
    ('经营性应付项目的增加', 'col148'),
    ('其他_BC', 'col149'),
])
Regist_this_to_account_list(BC1)

Regist_this_to_account_list(('债务转为资本', 'col151'))
Regist_this_to_account_list(('一年内到期的可转换公司债券', 'col152'))
Regist_this_to_account_list(('融资租入固定资产', 'col153'))

Regist_this_to_account_list(('现金等价物的期末余额', 'col156'))
Regist_this_to_account_list(('现金等价物的期初余额', 'col157'))
Regist_this_to_account_list(('现金及现金等价物净增加额', 'col237'))


# BC2 = ('现金及现金等价物净增加额', 'col237', [
#     ('现金的期末余额_BC',  'col154'),
#     ('减：现金的期初余额', 'col155', -1),
#     (经营活动产生的现金流量净额_BC, 1),
#     ('加：现金等价物的期末余额', 'col156'),
#     ('减：现金等价物的期初余额', 'col157'),

# ])



CEQ_END = ('现金等价物的期末余额', 'col156', [
    (accounts['期末现金及现金等价物余额'], -1),
    ('现金的期末余额',  'col154')
])
Regist_this_to_account_list(CEQ_END)

CEQ_BEG = ('现金等价物的期初余额', 'col157', [
    (accounts['期初现金及现金等价物余额'], -1),
    ('现金的期初余额',  'col155')
])
Regist_this_to_account_list(CEQ_BEG)

