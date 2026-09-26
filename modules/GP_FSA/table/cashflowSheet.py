from GP_FSA.core.table import Table
from GP_FSA import accounts

tbl_CS = Table()
tbl_CS.Item([
        accounts['销售商品提供劳务收到的现金'].copy().tag_level(1).tag_Name('销售商品、提供劳务收到的现金'),
        accounts['客户存款和同业存放款项净增加额'].copy().tag_level(1),
        accounts['向中央银行借款净增加额'].copy().tag_level(1),
        accounts['向其他金融机构拆入资金净增加额'].copy().tag_level(1),
        accounts['收到原保险合同保费取得的现金'].copy().tag_level(1),
        accounts['收到再保险业务现金净额'].copy().tag_level(1),
        accounts['保户储金及投资款净增加额'].copy().tag_level(1),
        accounts['收取利息手续费及佣金的现金'].copy().tag_level(1).tag_Name('收取利息、手续费及佣金的现金'),
        accounts['拆入资金净增加额'].copy().tag_level(1),
        accounts['回购业务资金净增加额'].copy().tag_level(1),
        accounts['收到的税费返还'].copy().tag_level(1),
        accounts['收到其他与经营活动有关的现金'].copy().tag_level(1),
        accounts['处置以公允价值计量且其变动计入当期损益的金融资产净增加额'].copy().tag_level(1),
    accounts['经营活动现金流入小计'].copy().Color('#e5e7eb').tag_Name('= 经营活动现金流入小计'),

        accounts['购买商品接受劳务支付的现金'].copy().tag_level(1).tag_Name('购买商品、接受劳务支付的现金'),
        accounts['客户贷款及垫款净增加额'].copy().tag_level(1),
        accounts['存放中央银行和同业款项净增加额'].copy().tag_level(1),
        accounts['支付原保险合同赔付款项的现金'].copy().tag_level(1),
        accounts['支付利息手续费及佣金的现金'].copy().tag_level(1).tag_Name('支付利息、手续费及佣金的现金'),
        accounts['支付保单红利的现金'].copy().tag_level(1),
        accounts['支付给职工以及为职工支付的现金'].copy().tag_level(1),
        accounts['支付的各项税费'].copy().tag_level(1),
        accounts['支付其他与经营活动有关的现金'].copy().tag_level(1),
    accounts['经营活动现金流出小计'].copy().Color('#e5e7eb').tag_Name('= 经营活动现金流入小计'),
    accounts['经营活动产生的现金流量净额'].copy().Color('red').tag_Name('一、经营活动产生的现金流量净额'),


        accounts['收回投资收到的现金'].copy().tag_level(1),
        accounts['取得投资收益收到的现金'].copy().tag_level(1),
        accounts['处置固定资产无形资产和其他长期资产收回的现金净额'].copy().tag_level(1).tag_Name('处置固定资产、无形资产和其他长期资产收回的现金净额'),
        accounts['处置子公司及其他营业单位收到的现金净额'].copy().tag_level(1),
        accounts['收到其他与投资活动有关的现金'].copy().tag_level(1),
    accounts['投资活动现金流入小计'].copy().Color('#e5e7eb').tag_Name('= 投资活动现金流入小计'),

        accounts['购建固定资产无形资产和其他长期资产支付的现金'].copy().tag_level(1).tag_Name('购建固定资产、无形资产和其他长期资产支付的现金'),
        accounts['投资支付的现金'].copy().tag_level(1),
        accounts['取得子公司及其他营业单位支付的现金净额'].copy().tag_level(1),
        accounts['支付其他与投资活动有关的现金'].copy().tag_level(1),
    accounts['投资活动现金流出小计'].copy().Color('#e5e7eb').tag_Name('= 投资活动现金流出小计'),
    accounts['投资活动产生的现金流量净额'].copy().Color('red').tag_Name('二、投资活动产生的现金流量净额'),


        accounts['吸收投资收到的现金'].copy().tag_level(1),
        accounts['子公司吸收少数股东投资收到的现金'].copy().tag_level(2).tag_Name('其中：子公司吸收少数股东投资收到的现金'),
        accounts['取得借款收到的现金'].copy().tag_level(1),
        accounts['收到其他与筹资活动有关的现金'].copy().tag_level(1),
    accounts['筹资活动现金流入小计'].copy().Color('#e5e7eb').tag_Name('= 筹资活动现金流入小计'),

        accounts['偿还债务支付的现金'].copy().tag_level(1),
        accounts['分配股利利润或偿付利息支付的现金'].copy().tag_level(1).tag_Name('分配股利、利润或偿付利息支付的现金'),
        accounts['子公司支付给少数股东的股利利润'].copy().tag_level(2).tag_Name('其中：子公司支付给少数股东的股利、利润'),
        accounts['支付其他与筹资活动有关的现金'].copy().tag_level(1),
    accounts['筹资活动现金流出小计'].copy().Color('#e5e7eb').tag_Name('= 筹资活动现金流出小计'),
    accounts['筹资活动产生的现金流量净额'].copy().Color('red').tag_Name('三、筹资活动产生的现金流量净额'),

    accounts['汇率变动对现金的影响'].copy().Color('red').tag_Name('四、汇率变动对现金的影响'),
        accounts['其他原因对现金的影响'].copy().tag_level(1),

    accounts['现金及现金等价物净增加额'].copy().Color('red').tag_Name('五、现金及现金等价物净增加额'),
        accounts['期初现金及现金等价物余额'].copy().tag_level(1).tag_Name('加：现金及现金等价物净增加额'),

    accounts['期末现金及现金等价物余额'].copy().Color('red').tag_Name('六、期末现金及现金等价物余额'),
])

tbl_CS2 = Table()
tbl_CS2.Item([
            accounts['经营活动产生的现金流量净额_经营活动净收益Tpct'].copy().tag_level(2).Color('green').tag_Name('经营活动产生的现金流量净额/经营活动净收益'),   
            accounts['经营净现金比率_短期债务T非金融'].copy().tag_level(2).Color('green').tag_Name('经营净现金比率/短期债务(非金融)'),   
            accounts['经营净现金比率_全部债务'].copy().tag_level(2).Color('green').tag_Name('经营净现金比率/全部债务'),   
            accounts['经营活动现金净流量与净利润比率'].copy().tag_level(2).Color('green').tag_Name('经营活动现金净流量/净利润'),   

    accounts['经营活动产生的现金流量净额'].copy().Color('#e5e7eb').tag_Name('一、经营活动产生的现金流量净额'),
        accounts['经营活动现金流入小计'].copy(),
        accounts['经营活动现金流出小计'].copy().Color('red').U(-1),

            accounts['销售商品提供劳务收到的现金'].copy().tag_level(1).tag_Name('销售商品、提供劳务收到的现金'),
                accounts['销售商品提供劳务收到的现金_营业收入Tpct'].copy().tag_level(2).Color('green').tag_Name('销售商品提供劳务收到的现金/营业收入'),   
            
            accounts['购买商品接受劳务支付的现金'].copy().tag_level(1).tag_Name('购买商品、接受劳务支付的现金').Color('red').U(-1),

            accounts['客户存款和同业存放款项净增加额'].copy().tag_level(1),
            accounts['客户贷款及垫款净增加额'].copy().tag_level(1).Color('red').U(-1),

            accounts['向中央银行借款净增加额'].copy().tag_level(1),
            accounts['向其他金融机构拆入资金净增加额'].copy().tag_level(1),
            accounts['存放中央银行和同业款项净增加额'].copy().tag_level(1).Color('red').U(-1),

            accounts['收到原保险合同保费取得的现金'].copy().tag_level(1),
            accounts['支付原保险合同赔付款项的现金'].copy().tag_level(1).Color('red').U(-1),

            accounts['收到再保险业务现金净额'].copy().tag_level(1),
            accounts['保户储金及投资款净增加额'].copy().tag_level(1),

            accounts['收取利息手续费及佣金的现金'].copy().tag_level(1).tag_Name('收取利息、手续费及佣金的现金'),
            accounts['支付利息手续费及佣金的现金'].copy().tag_level(1).tag_Name('支付利息、手续费及佣金的现金').Color('red').U(-1),

            accounts['拆入资金净增加额'].copy().tag_level(1),
            accounts['回购业务资金净增加额'].copy().tag_level(1),

            accounts['收到的税费返还'].copy().tag_level(1),
            accounts['支付的各项税费'].copy().tag_level(1).Color('red').U(-1),

            accounts['收到其他与经营活动有关的现金'].copy().tag_level(1),
            accounts['支付其他与经营活动有关的现金'].copy().tag_level(1).Color('red').U(-1),

            accounts['处置以公允价值计量且其变动计入当期损益的金融资产净增加额'].copy().tag_level(1),
            accounts['支付保单红利的现金'].copy().tag_level(1),
            accounts['支付给职工以及为职工支付的现金'].copy().tag_level(1),

    accounts['投资活动产生的现金流量净额'].copy().Color('#e5e7eb').tag_Name('二、投资活动产生的现金流量净额'),
        accounts['投资活动现金流入小计'].copy(),
        accounts['投资活动现金流出小计'].copy().Color('red').U(-1),

            accounts['收回投资收到的现金'].copy().tag_level(1),
            accounts['取得投资收益收到的现金'].copy().tag_level(1),
            accounts['投资支付的现金'].copy().tag_level(1).Color('red').U(-1),

            accounts['处置固定资产无形资产和其他长期资产收回的现金净额'].copy().tag_level(1).tag_Name('处置固定资产、无形资产和其他长期资产收回的现金净额'),
            accounts['购建固定资产无形资产和其他长期资产支付的现金'].copy().tag_level(1).tag_Name('购建固定资产、无形资产和其他长期资产支付的现金').Color('red').U(-1),
            
            accounts['处置子公司及其他营业单位收到的现金净额'].copy().tag_level(1),
            accounts['取得子公司及其他营业单位支付的现金净额'].copy().tag_level(1).Color('red').U(-1),
                accounts['资本支出_折旧和摊销'].copy().tag_level(2).Color('green').tag_Name('资本支出/折旧和摊销'),   

            accounts['收到其他与投资活动有关的现金'].copy().tag_level(1),
            accounts['支付其他与投资活动有关的现金'].copy().tag_level(1).Color('red').U(-1),


    accounts['筹资活动产生的现金流量净额'].copy().Color('#e5e7eb').tag_Name('三、筹资活动产生的现金流量净额'),
        accounts['筹资活动现金流入小计'].copy(),
        accounts['筹资活动现金流出小计'].copy().Color('red').U(-1),

            accounts['吸收投资收到的现金'].copy().tag_level(1),
            accounts['子公司吸收少数股东投资收到的现金'].copy().tag_level(2).tag_Name('其中：子公司吸收少数股东投资收到的现金'),

            accounts['分配股利利润或偿付利息支付的现金'].copy().tag_level(1).tag_Name('分配股利、利润或偿付利息支付的现金').Color('red').U(-1),
            accounts['子公司支付给少数股东的股利利润'].copy().tag_level(2).tag_Name('其中：子公司支付给少数股东的股利、利润').Color('red').U(-1),
            
            accounts['取得借款收到的现金'].copy().tag_level(1),
            accounts['偿还债务支付的现金'].copy().tag_level(1).Color('red').U(-1),

            accounts['收到其他与筹资活动有关的现金'].copy().tag_level(1),
            accounts['支付其他与筹资活动有关的现金'].copy().tag_level(1).Color('red').U(-1),

    accounts['汇率变动对现金的影响'].copy().Color('#e5e7eb').tag_Name('四、汇率变动对现金的影响'),
        accounts['其他原因对现金的影响'].copy().tag_level(1),

    accounts['现金及现金等价物净增加额'].copy().Color('#e5e7eb').tag_Name('五、现金及现金等价物净增加额'),
                accounts['每股现金流量净额'].copy().tag_level(2).Color('green').tag_Name('每股现金流量净额'),   
                accounts['全部资产现金回收率'].copy().tag_level(2).Color('green').tag_Name('全部资产现金回收率'),   

        accounts['期初现金及现金等价物余额'].copy().tag_level(1).tag_Name('加：现金及现金等价物净增加额'),

    accounts['期末现金及现金等价物余额'].copy().Color('#e5e7eb').tag_Name('六、期末现金及现金等价物余额'),
])
