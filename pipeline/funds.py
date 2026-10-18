"""Fund classification (decision 2, 2026-10-11): ETFs, closed-end funds and unit investment trusts are
excluded from the ownership output. Evidence, all from cached data (no manual lists):
  F1  registered investment company / UIT: the CIK filed any 1940-Act or UIT form in the EDGAR full index
      2010Q1-2015Q1 (N-CSR, N-Q, N-30D, N-MFP, N-1A, N-2, N-8*, N-14, NSAR-*, 485APOS/BPOS/BXT, 497*, 24F-2NT, S-6, 487).
      Catches open-end ETFs (iShares Trust, SPDR Series Trust, Vanguard), closed-end funds (Nuveen, BlackRock
      muni trusts) and UITs (SPY, QQQ, DIA).
  F2  commodity / currency exchange-traded product organised as a grantor trust or commodity pool (files 10-K,
      not 1940-Act): SIC 6221 in the SEC financial-statement data sets AND a fund-like name token
      (TRUST, FUND, SHARES, ETF, ISHARES, SPDR, POWERSHARES, PROSHARES, TEUCRIUM, CURRENCYSHARES).
  F3  the security itself is an exchange-traded note / fund per the SEC 13(f) list issuer name or description
      (ETF, ETN, ISHARES, SPDR, POWERSHERS, PROSHARES tokens; 'UNIT SER' / 'TR UNIT' unit-trust descriptions).
      Applied per 9-char CUSIP (an ETN's CUSIP prefix belongs to the issuing bank, e.g. Barclays Bank PLC).
  N   name-token only (for issuers with no CIK): 13(f) list name has FD/FDS/FUND/FUNDS/ETF/ETN/ISHARES/SPDR/
      POWERSHARES/PROSHARES/VANGUARD. Reported separately; it only affects the coverage denominator.
Usage: python3 -m pipeline.funds build   -> cache/parsed/fund_ciks.parquet + output/problems/fund_ciks.txt"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

FUND_FORM = re.compile(r"^(N-|NSAR|485[AB]|497|24F-2NT|S-6|487)")
F2_SIC = {"6221"}
F2_NAME = re.compile(r"\b(TRUST|FUND|SHARES|ETF|ISHARES|SPDR|POWERSHARES|PROSHARES|TEUCRIUM|CURRENCYSHARES)\b", re.I)
F3_TOKENS = re.compile(r"\b(ETF|ETN|ISHARES|SPDR|POWERSHARES|PROSHARES)\b", re.I)
F3_DESC = re.compile(r"\b(UNIT SER|TR UNIT|UTSER|UT SER|UNIT TR)\b", re.I)
N_TOKENS = re.compile(r"\b(FD|FDS|FUND|FUNDS|ETF|ETN|ISHARES|SPDR|POWERSHARES|PROSHARES|VANGUARD)\b", re.I)


def build() -> pd.DataFrame:
    idx = pd.read_parquet("cache/parsed/edgar_full_index_2010Q1_2015Q1.parquet", columns=["form_type", "company_name", "cik"])
    f1 = idx[idx["form_type"].str.match(FUND_FORM)]
    f1 = f1.groupby("cik").agg(n_fund_forms=("form_type", "size"), example_form=("form_type", "first"), name=("company_name", "last")).reset_index()
    f1["reason"] = "F1 1940-Act/UIT forms (" + f1["example_form"] + ")"
    sub = pd.read_parquet("cache/parsed/fsds_sub_all.parquet", columns=["cik", "name", "sic"]).drop_duplicates("cik", keep="last")
    f2 = sub[sub["sic"].isin(F2_SIC) & sub["name"].fillna("").str.contains(F2_NAME)].copy()
    f2["reason"] = "F2 SIC 6221 commodity pool/trust"
    out = pd.concat([f1[["cik", "name", "reason"]], f2[["cik", "name", "reason"]]]).drop_duplicates("cik")
    Path("output/problems").mkdir(parents=True, exist_ok=True)
    out.to_parquet("cache/parsed/fund_ciks.parquet", index=False)
    txt = (f"fund CIKs: {len(out):,} (F1 {len(f1):,}, F2 {len(f2):,} of which new {len(out) - len(f1):,})\n"
           f"F1 forms counted: {idx['form_type'][idx['form_type'].str.match(FUND_FORM)].value_counts().head(12).to_dict()}\n"
           f"F2 sample: {f2['name'].head(12).tolist()}")
    open("output/problems/fund_ciks.txt", "w").write(txt); print(txt)
    return out


def load() -> pd.DataFrame:
    return pd.read_parquet("cache/parsed/fund_ciks.parquet")


def f3_cusips(seclist: pd.DataFrame) -> pd.Series:
    """CUSIP9 -> reason for securities the 13(f) list itself marks as ETF/ETN/unit-trust units."""
    s = seclist.copy()
    hit = s["issuer_name"].str.contains(F3_TOKENS) | s["issuer_desc"].str.contains(F3_TOKENS) | s["issuer_desc"].str.contains(F3_DESC)
    r = s[hit].drop_duplicates("cusip").set_index("cusip")
    return pd.Series("F3 13(f) list ETF/ETN/unit (" + r["issuer_desc"].str.strip() + ")", index=r.index)


def name_token_cusip6(seclist: pd.DataFrame) -> pd.Series:
    s = seclist[seclist["issuer_name"].str.contains(N_TOKENS)].drop_duplicates("cusip6").set_index("cusip6")
    return pd.Series("N fund-like name token", index=s.index)


if __name__ == "__main__":
    build()
