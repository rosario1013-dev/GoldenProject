from GP_FSA import Caled

Caled('净资产比率').En('EquityRatio').Formula("归属于母公司股东权益总计/资产总计")
Caled('Net_Financing_Obli').En('NFO').Formula("(Financing_Obli-期末现金及现金等价物余额)")
Caled('Gearing Ratio').En('GearingRatio').Formula("Net_Financing_Obli/归属于母公司股东权益总计")



