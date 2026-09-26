from GP_FSA import Caled

Caled('营业总收入_1Y').En('Revenue').Formula("Ki(营业总收入_营业收入)")
Caled('营业利润_1Y').En('Op_Profit').Formula("Ki(营业利润)")
Caled('净利润_1Y').En('SUM_Profit').Formula("Ki(持续经营净利润+终止经营净利润)")
Caled('税务成本_1Y').En('SUM_tax').Formula("Ki(所得税)")
