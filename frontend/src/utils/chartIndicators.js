/** Sub-pane technical indicators (MACD / RSI / KDJ) + BOLL overlay. */

export const INDICATOR_OPTIONS = [
  { key: 'macd', label: 'MACD', pane: true },
  { key: 'rsi', label: 'RSI', pane: true },
  { key: 'kdj', label: 'KDJ', pane: true },
  { key: 'boll', label: 'BOLL', pane: false },
];

export const INDICATOR_PANE_HEIGHT = 110;
/** Visual gap between K-line / indicator panes (px). */
export const PANE_SEPARATOR_GAP = 8;

export const INDICATOR_COLORS = {
  macdDif: '#f5a623',
  macdDea: '#2f7ed8',
  macdUp: 'rgba(239, 83, 80, 0.7)',
  macdDown: 'rgba(38, 166, 154, 0.7)',
  rsi6: '#ef5350',
  rsi12: '#f5a623',
  rsi24: '#2f7ed8',
  kdjK: '#f5a623',
  kdjD: '#2f7ed8',
  kdjJ: '#9b59b6',
  bollMid: '#90a4ae',
  bollUpper: '#78909c',
  bollLower: '#78909c',
};

export function defaultIndicatorEnabled() {
  return {
    macd: true,
    rsi: true,
    kdj: false,
    boll: false,
  };
}

export function enabledIndicatorKinds(enabled) {
  return INDICATOR_OPTIONS.map((o) => o.key).filter((key) => enabled?.[key]);
}

export function paneIndicatorKinds(enabled) {
  return INDICATOR_OPTIONS.filter((o) => o.pane && enabled?.[o.key]).map((o) => o.key);
}

export function chartHeightWithIndicators(baseHeight, enabled) {
  const panes = paneIndicatorKinds(enabled).length;
  if (panes <= 0) return baseHeight;
  return baseHeight + panes * INDICATOR_PANE_HEIGHT + panes * PANE_SEPARATOR_GAP;
}

/** Build {time -> {macd_dif, ...}} lookup for crosshair tooltip. */
export function buildIndicatorLookup(series) {
  const byTime = new Map();
  if (!series) return byTime;

  const add = (points, field) => {
    for (const pt of points ?? []) {
      if (!pt?.time || pt.value == null) continue;
      const row = byTime.get(pt.time) ?? {};
      row[field] = pt.value;
      byTime.set(pt.time, row);
    }
  };

  if (series.macd) {
    add(series.macd.dif, 'macd_dif');
    add(series.macd.dea, 'macd_dea');
    add(series.macd.hist, 'macd');
  }
  if (series.rsi) {
    add(series.rsi.rsi_6, 'rsi_6');
    add(series.rsi.rsi_12, 'rsi_12');
    add(series.rsi.rsi_24, 'rsi_24');
  }
  if (series.kdj) {
    add(series.kdj.k, 'kdj_k');
    add(series.kdj.d, 'kdj_d');
    add(series.kdj.j, 'kdj_j');
  }
  if (series.boll) {
    add(series.boll.mid, 'boll_mid');
    add(series.boll.upper, 'boll_upper');
    add(series.boll.lower, 'boll_lower');
  }
  return byTime;
}

export function withMacdColors(histPoints) {
  return (histPoints ?? []).map((pt) => ({
    ...pt,
    color: pt.value >= 0 ? INDICATOR_COLORS.macdUp : INDICATOR_COLORS.macdDown,
  }));
}

export function formatIndicatorValue(value, digits = 2) {
  if (value == null || Number.isNaN(value)) return '--';
  return Number(value).toFixed(digits);
}

function num(value) {
  if (value == null || Number.isNaN(Number(value))) return null;
  return Number(value);
}

/**
 * Derive status badges from the latest (and previous) indicator snapshot.
 * Used for top-right chart notices.
 */
export function deriveIndicatorStatuses({ last, prev, enabled, changePct } = {}) {
  const badges = [];
  if (!last) return badges;

  if (enabled?.macd) {
    const dif = num(last.macd_dif);
    const dea = num(last.macd_dea);
    const hist = num(last.macd);
    const prevDif = num(prev?.macd_dif);
    const prevDea = num(prev?.macd_dea);
    const crossedUp =
      prevDif != null && prevDea != null && dif != null && dea != null && prevDif < prevDea && dif >= dea;
    const crossedDown =
      prevDif != null && prevDea != null && dif != null && dea != null && prevDif > prevDea && dif <= dea;

    if (crossedUp) {
      badges.push({
        id: 'macd-cross-up',
        label: 'MACD金叉',
        tone: 'bull',
        detail: `DIF 上穿 DEA（DIF=${formatIndicatorValue(dif)}, DEA=${formatIndicatorValue(dea)}, 柱=${formatIndicatorValue(hist)}），短线动能转强。`,
      });
    } else if (crossedDown) {
      badges.push({
        id: 'macd-cross-down',
        label: 'MACD死叉',
        tone: 'bear',
        detail: `DIF 下穿 DEA（DIF=${formatIndicatorValue(dif)}, DEA=${formatIndicatorValue(dea)}, 柱=${formatIndicatorValue(hist)}），短线动能转弱。`,
      });
    } else if (hist != null && hist > 0) {
      badges.push({
        id: 'macd-bull',
        label: 'MACD多头',
        tone: 'bull',
        detail: `MACD 柱为正（${formatIndicatorValue(hist)}），DIF=${formatIndicatorValue(dif)}, DEA=${formatIndicatorValue(dea)}，多头占优。`,
      });
    } else if (hist != null && hist < 0) {
      badges.push({
        id: 'macd-bear',
        label: 'MACD空头',
        tone: 'bear',
        detail: `MACD 柱为负（${formatIndicatorValue(hist)}），DIF=${formatIndicatorValue(dif)}, DEA=${formatIndicatorValue(dea)}，空头占优。`,
      });
    }
  }

  if (enabled?.rsi) {
    const rsi6 = num(last.rsi_6);
    const rsi12 = num(last.rsi_12);
    const rsi24 = num(last.rsi_24);
    const prev6 = num(prev?.rsi_6);
    const prev12 = num(prev?.rsi_12);
    const primary = rsi6 ?? rsi12 ?? rsi24;

    const crossedUp =
      prev6 != null && prev12 != null && rsi6 != null && rsi12 != null && prev6 < prev12 && rsi6 >= rsi12;
    const crossedDown =
      prev6 != null && prev12 != null && rsi6 != null && rsi12 != null && prev6 > prev12 && rsi6 <= rsi12;

    if (crossedUp) {
      badges.push({
        id: 'rsi-cross-up',
        label: 'RSI金叉',
        tone: 'bull',
        detail: `RSI6 上穿 RSI12（RSI6=${formatIndicatorValue(rsi6, 1)}, RSI12=${formatIndicatorValue(rsi12, 1)}, RSI24=${formatIndicatorValue(rsi24, 1)}），短线动能转强。`,
      });
    } else if (crossedDown) {
      badges.push({
        id: 'rsi-cross-down',
        label: 'RSI死叉',
        tone: 'bear',
        detail: `RSI6 下穿 RSI12（RSI6=${formatIndicatorValue(rsi6, 1)}, RSI12=${formatIndicatorValue(rsi12, 1)}, RSI24=${formatIndicatorValue(rsi24, 1)}），短线动能转弱。`,
      });
    }

    if (primary != null && primary >= 80) {
      badges.push({
        id: 'rsi-ob',
        label: 'RSI超买',
        tone: 'warn',
        detail: `RSI6=${formatIndicatorValue(rsi6, 1)}, RSI12=${formatIndicatorValue(rsi12, 1)}, RSI24=${formatIndicatorValue(rsi24, 1)}。短期涨幅较大，注意回调风险。`,
      });
    } else if (primary != null && primary <= 20) {
      badges.push({
        id: 'rsi-os',
        label: 'RSI超卖',
        tone: 'bull',
        detail: `RSI6=${formatIndicatorValue(rsi6, 1)}, RSI12=${formatIndicatorValue(rsi12, 1)}, RSI24=${formatIndicatorValue(rsi24, 1)}。短期跌幅较大，或有反弹机会。`,
      });
    } else if (primary != null && primary >= 60) {
      badges.push({
        id: 'rsi-strong',
        label: 'RSI偏强',
        tone: 'bull',
        detail: `RSI6=${formatIndicatorValue(rsi6, 1)}, RSI12=${formatIndicatorValue(rsi12, 1)}, RSI24=${formatIndicatorValue(rsi24, 1)}，处于偏强区域（≥60）。`,
      });
    } else if (primary != null && primary <= 40) {
      badges.push({
        id: 'rsi-weak',
        label: 'RSI偏弱',
        tone: 'bear',
        detail: `RSI6=${formatIndicatorValue(rsi6, 1)}, RSI12=${formatIndicatorValue(rsi12, 1)}, RSI24=${formatIndicatorValue(rsi24, 1)}，处于偏弱区域（≤40）。`,
      });
    }
    // 40–60：不显示“中性”，避免每只股票都刷一条无信息量告示
  }

  if (enabled?.kdj) {
    const k = num(last.kdj_k);
    const d = num(last.kdj_d);
    const j = num(last.kdj_j);
    const prevK = num(prev?.kdj_k);
    const prevD = num(prev?.kdj_d);
    const crossedUp = prevK != null && prevD != null && k != null && d != null && prevK < prevD && k >= d;
    const crossedDown = prevK != null && prevD != null && k != null && d != null && prevK > prevD && k <= d;

    if (crossedUp) {
      badges.push({
        id: 'kdj-cross-up',
        label: 'KDJ金叉',
        tone: 'bull',
        detail: `K 上穿 D（K=${formatIndicatorValue(k, 1)}, D=${formatIndicatorValue(d, 1)}, J=${formatIndicatorValue(j, 1)}），短线偏向转强。`,
      });
    } else if (crossedDown) {
      badges.push({
        id: 'kdj-cross-down',
        label: 'KDJ死叉',
        tone: 'bear',
        detail: `K 下穿 D（K=${formatIndicatorValue(k, 1)}, D=${formatIndicatorValue(d, 1)}, J=${formatIndicatorValue(j, 1)}），短线偏向转弱。`,
      });
    } else if (j != null && j >= 100) {
      badges.push({
        id: 'kdj-ob',
        label: 'KDJ超买',
        tone: 'warn',
        detail: `J=${formatIndicatorValue(j, 1)}（K=${formatIndicatorValue(k, 1)}, D=${formatIndicatorValue(d, 1)}），短线偏热。`,
      });
    } else if (j != null && j <= 0) {
      badges.push({
        id: 'kdj-os',
        label: 'KDJ超卖',
        tone: 'bull',
        detail: `J=${formatIndicatorValue(j, 1)}（K=${formatIndicatorValue(k, 1)}, D=${formatIndicatorValue(d, 1)}），短线偏冷。`,
      });
    }
  }

  if (enabled?.boll) {
    const mid = num(last.boll_mid);
    const upper = num(last.boll_upper);
    const lower = num(last.boll_lower);
    const close = num(last.close);
    if (close != null && upper != null && mid != null && lower != null && upper > lower) {
      const pos = (close - lower) / (upper - lower);
      if (close >= upper) {
        badges.push({
          id: 'boll-upper',
          label: '触及上轨',
          tone: 'warn',
          detail: `收盘价触及/突破布林上轨（上=${formatIndicatorValue(upper)}, 中=${formatIndicatorValue(mid)}, 下=${formatIndicatorValue(lower)}），波动偏强。`,
        });
      } else if (close <= lower) {
        badges.push({
          id: 'boll-lower',
          label: '触及下轨',
          tone: 'bull',
          detail: `收盘价触及/跌破布林下轨（上=${formatIndicatorValue(upper)}, 中=${formatIndicatorValue(mid)}, 下=${formatIndicatorValue(lower)}），或有超跌反弹。`,
        });
      } else if (pos >= 0.7) {
        badges.push({
          id: 'boll-high',
          label: '轨道偏上',
          tone: 'neutral',
          detail: `价格位于布林带上方区域（相对位置 ${(pos * 100).toFixed(0)}%）。`,
        });
      } else if (pos <= 0.3) {
        badges.push({
          id: 'boll-low',
          label: '轨道偏下',
          tone: 'neutral',
          detail: `价格位于布林带下方区域（相对位置 ${(pos * 100).toFixed(0)}%）。`,
        });
      }
    }
  }

  // Volume vs VMA5/VMA10 — always available on main chart (not gated by checkbox)
  {
    const vol = num(last.volume);
    const vma5 = num(last.vma5);
    const vma10 = num(last.vma10);
    const prevVma5 = num(prev?.vma5);
    const prevVma10 = num(prev?.vma10);
    const fmtVol = (v) =>
      v == null ? '--' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 0 });

    const crossedUp =
      prevVma5 != null &&
      prevVma10 != null &&
      vma5 != null &&
      vma10 != null &&
      prevVma5 < prevVma10 &&
      vma5 >= vma10;
    const crossedDown =
      prevVma5 != null &&
      prevVma10 != null &&
      vma5 != null &&
      vma10 != null &&
      prevVma5 > prevVma10 &&
      vma5 <= vma10;

    if (crossedUp) {
      badges.push({
        id: 'vma-cross-up',
        label: '量能金叉',
        tone: 'bull',
        detail: `VMA5 上穿 VMA10（VMA5=${fmtVol(vma5)}, VMA10=${fmtVol(vma10)}），短期量能转强。`,
      });
    } else if (crossedDown) {
      badges.push({
        id: 'vma-cross-down',
        label: '量能死叉',
        tone: 'bear',
        detail: `VMA5 下穿 VMA10（VMA5=${fmtVol(vma5)}, VMA10=${fmtVol(vma10)}），短期量能转弱。`,
      });
    }

    if (vol != null && vma5 != null && vma10 != null) {
      if (vol > vma5 * 1.5 && vol > vma10) {
        badges.push({
          id: 'vol-surge',
          label: '显著放量',
          tone: 'warn',
          detail: `成交量 ${fmtVol(vol)} 明显高于 VMA5 ${fmtVol(vma5)} / VMA10 ${fmtVol(vma10)}（>1.5×VMA5），交投显著放大。`,
        });
      } else if (vol < vma5 * 0.5 && vol < vma10) {
        badges.push({
          id: 'vol-dry',
          label: '显著缩量',
          tone: 'neutral',
          detail: `成交量 ${fmtVol(vol)} 明显低于 VMA5 ${fmtVol(vma5)} / VMA10 ${fmtVol(vma10)}（<0.5×VMA5），交投显著萎缩。`,
        });
      } else if (vol > vma5 && vol > vma10) {
        badges.push({
          id: 'vol-up',
          label: '放量',
          tone: 'bull',
          detail: `成交量 ${fmtVol(vol)} > VMA5 ${fmtVol(vma5)} / VMA10 ${fmtVol(vma10)}，短中期均量上方，交投活跃。`,
        });
      } else if (vol < vma5 && vol < vma10) {
        badges.push({
          id: 'vol-down',
          label: '缩量',
          tone: 'bear',
          detail: `成交量 ${fmtVol(vol)} < VMA5 ${fmtVol(vma5)} / VMA10 ${fmtVol(vma10)}，短中期均量下方，交投偏淡。`,
        });
      }
    }
  }

  if (changePct != null && !Number.isNaN(changePct)) {
    if (changePct > 0) {
      badges.push({
        id: 'day-up',
        label: `日涨${changePct.toFixed(2)}%`,
        tone: 'bull',
        detail: `最近交易日涨幅 ${changePct.toFixed(2)}%（相对前一交易日不复权收盘价）。`,
      });
    } else if (changePct < 0) {
      badges.push({
        id: 'day-down',
        label: `日跌${Math.abs(changePct).toFixed(2)}%`,
        tone: 'bear',
        detail: `最近交易日跌幅 ${changePct.toFixed(2)}%（相对前一交易日不复权收盘价）。`,
      });
    }
  }

  return badges;
}
