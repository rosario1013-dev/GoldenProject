"""Generate test_gp_tdx.ipynb — single notebook for all GP_TDX modules."""

import json
from pathlib import Path

DIR = Path(__file__).resolve().parent
MODULES_ROOT = DIR.parent  # .../modules — add to sys.path for `import GP_TDX`

NB_META = {
    "kernelspec": {"display_name": "K_VENV", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.14.0"},
}

PROJECT_ROOT_STR = str(MODULES_ROOT).replace("\\", "/")


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


cells = [
    md(
        "# GP_TDX — module tests\n\n"
        "Tests for **quote**, **cw**, **dividend**, and **stockinfo** upload to MongoDB.\n\n"
        "- Set `UPLOAD_TO_MONGO = True` to write to MongoDB (default: read-only).\n"
        "- Use filter variables in each section for partial uploads.\n"
        "- CLI equivalents: `python -m GP_TDX quote --date 2026-06-17`, etc.\n"
    ),
    code(
        f"""import sys
sys.path.insert(0, r'{PROJECT_ROOT_STR}')

from GP_TDX.config import Config, DEFAULT_CONFIG
from GP_TDX.db import TdxDB

# Set True to upsert into MongoDB
UPLOAD_TO_MONGO = False

config = DEFAULT_CONFIG
print('GP_TDX version:', __import__('GP_TDX').__version__)
print('TDX path:', config.tdx_path)
print('Mongo DB:', config.mongo_db)
"""
    ),
    # --- QUOTE ---
    md(
        "## 1. Quote (`GP_TDX.quote`)\n\n"
        "- Source: `vipdoc/{{sh,sz,bj}}/lday/*.day`\n"
        "- Target: `tdx.QUATE` (key: IDE + DT)\n"
        "- Filters: `QUOTE_DATE`, `QUOTE_DATE_FROM` / `QUOTE_DATE_TO`, `QUOTE_YEAR`, `QUOTE_IDES`\n"
    ),
    code(
        """from GP_TDX.quote import all_lday_files, read_lday_file, upload_quote_file, upload_all_quotes
from GP_TDX.utils import filter_by_date

# Filter options — leave None for full upload
QUOTE_DATE = '2026-06-17'      # one trading day
QUOTE_DATE_FROM = None         # e.g. '2026-01-01'
QUOTE_DATE_TO = None           # e.g. '2026-06-30'
QUOTE_YEAR = None              # e.g. 2026
QUOTE_IDES = None              # e.g. ['sh689009', 'sh600519']

quote_files = all_lday_files(config=config, ides=QUOTE_IDES)
print(f'Found {len(quote_files):,} .day files')

sample_quote_file = r'C:/zd_zsone/vipdoc/sh/lday/sh689009.day'
quote_df = read_lday_file(sample_quote_file)
print('Sample shape:', quote_df.shape)
quote_df[['IDE', 'DT', 'O', 'H', 'L', 'C', 'V']].tail(5)
"""
    ),
    code(
        """filtered_quote = filter_by_date(
    quote_df,
    date=QUOTE_DATE,
    date_from=QUOTE_DATE_FROM,
    date_to=QUOTE_DATE_TO,
    year=QUOTE_YEAR,
)
print('Rows after filter:', len(filtered_quote))
filtered_quote.head()
"""
    ),
    code(
        """if UPLOAD_TO_MONGO:
    result = upload_all_quotes(
        config=config,
        date=QUOTE_DATE,
        date_from=QUOTE_DATE_FROM,
        date_to=QUOTE_DATE_TO,
        year=QUOTE_YEAR,
        ides=QUOTE_IDES,
        show_progress=True,
    )
    print(result)
    db = TdxDB(config)
    doc = db.collection('QUATE').find_one({'IDE': 'sh689009'}, sort=[('DT', -1)])
    print('Latest QUATE doc:', doc)
    db.close()
else:
    print('UPLOAD_TO_MONGO=False, skip quote upload.')
"""
    ),
    # --- CW ---
    md(
        "## 2. CW (`GP_TDX.cw`)\n\n"
        "- Source: `vipdoc/cw/gpcw*.dat`\n"
        "- Target: `tdx.CW` (key: IDE + REPORTDATE)\n"
        "- Filters: `CW_QUARTER` (e.g. `2026Q1`) or `CW_REPORT_DATE` (e.g. `2026-03-31`)\n"
    ),
    code(
        """from pathlib import Path
from GP_TDX.cw import all_cw_files, read_cw_file, upload_all_cw, select_cw_files

CW_QUARTER = '2026Q1'          # or None for all quarters
CW_REPORT_DATE = None          # or '2026-03-31'

cw_files = all_cw_files(config=config)
print(f'All gpcw files: {len(cw_files)}')

cw_target_files = select_cw_files(
    config=config,
    quarter=CW_QUARTER,
    report_date=CW_REPORT_DATE,
)
print('Selected:', [Path(f).name for f in cw_target_files])

cw_sample_file = cw_target_files[0]
cw_df = read_cw_file(cw_sample_file)
print('Rows:', len(cw_df))
cw_df[['IDE', 'CODE', 'REPORTDATE']].head(10)
"""
    ),
    code(
        """if UPLOAD_TO_MONGO:
    result = upload_all_cw(
        config=config,
        quarter=CW_QUARTER,
        report_date=CW_REPORT_DATE,
        show_progress=True,
    )
    print(result)
    db = TdxDB(config)
    ide = cw_df.iloc[0]['IDE']
    doc = db.collection('CW').find_one({'IDE': ide})
    print('Sample CW doc keys:', list(doc.keys())[:12], '...')
    db.close()
else:
    print('UPLOAD_TO_MONGO=False, skip CW upload.')
"""
    ),
    # --- DIVIDEND ---
    md(
        "## 3. Dividend (`GP_TDX.dividend`)\n\n"
        "- Source: `T0002/hq_cache/gbbq` → readjust → FHZGB + PKV\n"
        "- Target: `tdx.FHZGB`, `tdx.STOCK_PKVZGB`\n"
        "- Filter: `DIVIDEND_YEAR` (full history still processed for correct PKV)\n"
    ),
    code(
        """from GP_TDX.dividend import (
    load_gbbq,
    readjust,
    add_pkv,
    process_all_gbbq,
    extract_dividend_df,
    upload_dividend,
)
from GP_TDX.utils import filter_by_year

DIVIDEND_YEAR = 2025   # or None for all years

gbbq_df = load_gbbq(config=config)
print(f'Raw gbbq: {len(gbbq_df):,} records, {gbbq_df["IDE"].nunique():,} stocks')
gbbq_df.head()
"""
    ),
    code(
        """sample_ide = 'sh600519'
sample_adj = readjust(gbbq_df[gbbq_df['IDE'] == sample_ide].reset_index(drop=True))
sample_pkv = add_pkv(sample_adj)
cols = ['IDE', 'DT', 'CAT', 'XJBL', 'SZZBL', 'P', 'PKV', 'ZGB']
sample_pkv[cols].dropna(subset=['XJBL'], how='all').tail(10)
"""
    ),
    code(
        """print('Processing all stocks (may take ~1 min)...')
fhzgb_df = process_all_gbbq(gbbq_df)
dividend_df = extract_dividend_df(fhzgb_df)
year_df = filter_by_year(fhzgb_df, DIVIDEND_YEAR) if DIVIDEND_YEAR else fhzgb_df

print(f'FHZGB total: {len(fhzgb_df):,}')
print(f'FHZGB for {DIVIDEND_YEAR or "all years"}: {len(year_df):,}')
print(f'Dividend records: {len(dividend_df):,}')
dividend_df.head(10)
"""
    ),
    code(
        """if UPLOAD_TO_MONGO:
    result = upload_dividend(config=config, year=DIVIDEND_YEAR)
    print(result)
    db = TdxDB(config)
    print('FHZGB count:', db.collection('FHZGB').count_documents({}))
    print('STOCK_PKVZGB count:', db.collection('STOCK_PKVZGB').count_documents({}))
    db.close()
else:
    print('UPLOAD_TO_MONGO=False, skip dividend upload.')
"""
    ),
    # --- STOCKINFO ---
    md(
        "## 4. Stockinfo (`GP_TDX.stockinfo`)\n\n"
        "- Stock list → `tdx.STOCK`\n"
        "- F10 company profiles → `tdx.STOCKINFO`\n"
    ),
    code(
        """from GP_TDX.stockinfo import (
    build_a_share_list,
    fetch_company_profiles,
    upload_stock_list,
    upload_stockinfo,
    upload_all_stockinfo,
)

STOCKINFO_SAMPLE = 5   # F10 batch size for testing

stock_df = build_a_share_list(config=config)
print(f'A-share stocks: {len(stock_df):,}')
stock_df.head(10)
"""
    ),
    code(
        """profile_df = fetch_company_profiles(['sz002407'], config=config, show_progress=False)
profile_df.T
"""
    ),
    code(
        """batch = fetch_company_profiles(
    stock_df['IDE'].head(STOCKINFO_SAMPLE).tolist(),
    config=config,
    show_progress=True,
)
batch[['IDE', 'company_name', 'website', 'registered_address', 'main_business']]
"""
    ),
    code(
        """if UPLOAD_TO_MONGO:
    stock_result = upload_stock_list(config=config, stock_df=stock_df)
    print('STOCK:', stock_result)

    info_result = upload_stockinfo(
        config=config,
        ides=stock_df['IDE'].head(10).tolist(),
        show_progress=True,
    )
    print('STOCKINFO:', info_result)

    db = TdxDB(config)
    print('STOCK count:', db.collection('STOCK').count_documents({}))
    print('STOCKINFO count:', db.collection('STOCKINFO').count_documents({}))
    db.close()
else:
    print('UPLOAD_TO_MONGO=False, skip stockinfo upload.')
"""
    ),
]

out = DIR / "test_gp_tdx.ipynb"
out.write_text(
    json.dumps({"cells": cells, "metadata": NB_META, "nbformat": 4, "nbformat_minor": 5}, ensure_ascii=False, indent=1),
    encoding="utf-8",
)
print("created", out.name)

# remove old per-module notebooks
for old in ("test_quote.ipynb", "test_cw.ipynb", "test_dividend.ipynb", "test_stockinfo.ipynb"):
    path = DIR / old
    if path.exists():
        path.unlink()
        print("deleted", old)

print("done")
