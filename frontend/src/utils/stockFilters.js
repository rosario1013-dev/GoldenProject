export const DEFAULT_STOCK_FILTERS = {
  excludeChiNext: false,
  excludeStar: false,
  excludeBj: false,
  excludeSt: false,
};

export const ALL_STOCK_FILTERS = {
  excludeChiNext: true,
  excludeStar: true,
  excludeBj: true,
  excludeSt: true,
};

export function isAllFiltersEnabled(filters) {
  return (
    filters.excludeChiNext
    && filters.excludeStar
    && filters.excludeBj
    && filters.excludeSt
  );
}

export function isAnyFilterEnabled(filters) {
  return (
    filters.excludeChiNext
    || filters.excludeStar
    || filters.excludeBj
    || filters.excludeSt
  );
}

/** 创业板：sz3 开头 */
export function isChiNextStock(ide) {
  return /^sz3/i.test(ide ?? '');
}

/** 科创板：sh68 开头 */
export function isStarMarketStock(ide) {
  return /^sh68/i.test(ide ?? '');
}

/** 北证 A 股：bj 开头 */
export function isBjStock(ide) {
  return /^bj/i.test(ide ?? '');
}

/** ST 股：名称以 ST 开头（含 *ST） */
export function isStStock(name) {
  const trimmed = (name ?? '').trim();
  return /^(\*?ST)/i.test(trimmed);
}

export function filterStocks(stocks, filters) {
  if (!stocks?.length) return [];
  return stocks.filter((stock) => {
    const { ide, name } = stock;
    if (filters.excludeChiNext && isChiNextStock(ide)) return false;
    if (filters.excludeStar && isStarMarketStock(ide)) return false;
    if (filters.excludeBj && isBjStock(ide)) return false;
    if (filters.excludeSt && isStStock(name)) return false;
    return true;
  });
}
