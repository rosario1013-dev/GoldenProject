from GP_FSA import accounts
from GP_FSA.valuation.PE import PB_from_fiexed_COE, func_logize, FairX_Realized_Required, logize
import pandas
from GP_KDB import KDB


def main_FSA(self):
    v = accounts['BPS'].value(self)
    v.index.name = 'REPORTDATE'
    v.name = 'BPS'
    df = pandas.DataFrame(v)


    # Equaty의 위험수준별구조를 위한 지표들
    df['BPS_low'] = accounts['BPS_low'].value(self)
    df['BPS_low_low'] = accounts['BPS_low_low'].value(self)

    # 수입-지출구조를 위한 지표들
    df['Op_Revenue_PS'] = self.PS(accounts['Op_Revenue'].value(self))
    df['Op_Cost_PS'] = self.PS(accounts['Op_Cost'].value(self))
    df['Op_fixed_Cost_PS'] = self.PS(accounts['Op_fixed_Cost'].value(self))
    df['Op_fixed_Cost_without_DA_PS'] = self.PS(accounts['Op_fixed_Cost_without_DA'].value(self))
    df['BPS_and_Op_NetCashflow_PS'] = self.PS(accounts['Op_NetCashflow'].value(self) + accounts['归属于母公司股东权益总计'].value(self))

    df['cashin_OP_PS'] = self.PS(accounts['cashin_OP'].value(self))
    df['cashout_OP_PS'] = self.PS(accounts['cashout_OP'].value(self))

    df['고유PB'] = accounts['净资产收益率_1Y'].value(self).apply(lambda x: logize(FairX_Realized_Required(x, 0.085)))
    df['고유BPS'] = df['BPS'] + df['고유PB']
    # Chart overlay alias (same price scale as BPS / FDK).
    df['固有PB'] = df['고유BPS']

    df['Fair_PB_1'] = df['BPS'] + accounts['Op_EBITDA_revenue'].value(self).apply(
        lambda x: logize(FairX_Realized_Required(x, 0.10)))
    df['Fair_PB_2'] = df['BPS'] + accounts['Op_EBITDA_revenue'].value(self).apply(
        lambda x: logize(FairX_Realized_Required(x, 0.15)))
    df['Fair_PB_3'] = df['BPS'] + accounts['Op_EBITDA_revenue'].value(self).apply(
        lambda x: logize(FairX_Realized_Required(x, 0.20)))
    df['Fair_PB_4'] = df['BPS'] + accounts['Op_EBITDA_revenue'].value(self).apply(
        lambda x: logize(FairX_Realized_Required(x, 0.25)))

    # df['C_EBITDA'] = self.PS(accounts['YEBITDA'].value(self))


    df['C_BPS加5年净利润'] = accounts['BPS加5年净利润'].value(self)
    df['C_每股基本营业收入'] = accounts['每股基本营业收入'].value(self)
    df['C_每股基本营业成本'] = accounts['每股基本营业成本'].value(self)

    df['C_净资产收益率_1Y'] = accounts['净资产收益率_1Y'].value(self)


    # op에서 필요한 자료
    df['C_营业总收入_1Y'] = accounts['营业总收入_1Y'].value(self)
    df['C_营业总收入_dY'] = df['C_营业总收入_1Y'] - df['C_营业总收入_1Y'].shift(4)
    df['YEBIT'] = accounts['YEBIT'].value(self)
    df['C_营业利润_1Y'] = accounts['营业利润_1Y'].value(self)
    df['C_净利润_1Y'] = accounts['净利润_1Y'].value(self)
    df['C_税务成本_1Y'] = accounts['税务成本_1Y'].value(self)
    df['C_归属于母公司股东权益总计'] = accounts['归属于母公司股东权益总计'].value(self)
    df['C_归属于母公司股东权益总计_dY'] = df['C_归属于母公司股东权益总计'] - df['C_归属于母公司股东权益总计'].shift(4)

    df['C_股本投入'] = accounts['实收资本'].value(self) + accounts['其他权益工具_EQ'].value(self) + accounts[
        '资本公积'].value(self)

    df['C_负债合计'] = accounts['负债合计'].value(self)
    df['C_负债合计_dY'] = df['C_负债合计'] - df['C_负债合计'].shift(4)
    df['C_流动负债合计'] = accounts['流动负债合计'].value(self)
    df['C_流动负债合计_dY'] = df['C_流动负债合计'] - df['C_流动负债合计'].shift(4)
    df['C_少数股东权益'] = accounts['少数股东权益_EQ'].value(self)

    df['C_每股流动资产合计'] = accounts['FQ每股流动资产'].value(self)
    df['C_FQ每股净流动资产'] = accounts['FQ每股净流动资产'].value(self)

    df['C_EBIT'] = accounts['YEBIT_PS'].value(self)
    df['C_EBITDA'] = accounts['YEBITDA_PS'].value(self)

    df = df.reset_index()
    df['DTnum'] = df['REPORTDATE'].apply(lambda DT: KDB().EDTs.get(DT, 0))

    return df