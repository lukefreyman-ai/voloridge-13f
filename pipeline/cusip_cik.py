"""CUSIP -> company CIK map from 13G/13D links (Stage 2), with validation.
  python3 -m pipeline.cusip_cik build <label> <sc13_label>
Writes data/<label>_cusip_cik_map.csv (cusip6, cusip9, company_cik, company_name, map_source, evidence_accession,
evidence_date, n_links, conflict_flag) and output/problems/<label>/cusip_cik_validation.txt."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

from .cusip import is_valid9

STOP = {"INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LLC", "LP", "PLC", "HOLDINGS", "HLDGS", "GROUP", "GRP",
        "THE", "OF", "AND", "&", "TRUST", "TR", "COM", "NEW", "DEL", "INCORPORATED", "SA", "NV", "AG", "CL", "CLASS", "A", "B"}


def norm_tokens(name: str) -> set:
    toks = re.sub(r"[^A-Z0-9 ]", " ", (name or "").upper()).split()
    return {t for t in toks if t not in STOP and len(t) > 1}


def build(label: str, sc13_label: str):
    links = pd.read_parquet(f"cache/parsed/{sc13_label}_sc13_links.parquet")
    links = links[links["cusip"].notna() & links["subject_cik"].notna()].copy()
    links["cusip"] = links["cusip"].str.upper()
    links = links[links["cusip"].str.len() == 9]
    links["valid_check_digit"] = links["cusip"].map(is_valid9)
    links["cusip6"] = links["cusip"].str[:6]
    links["subject_cik"] = links["subject_cik"].astype(int)
    out = [f"{label}: CUSIP->CIK from {sc13_label} ({len(links):,} 13G/13D filings with a CUSIP and a subject CIK)"]
    out.append(f"check digit valid: {links['valid_check_digit'].sum():,} / {len(links):,} = {links['valid_check_digit'].mean():.1%} of links; "
               f"distinct CUSIPs {links['cusip'].nunique():,}, valid {links.loc[links['valid_check_digit'], 'cusip'].nunique():,}")
    links = links[links["valid_check_digit"]]
    # one row per (cusip9, cik): count of filings, latest filing as evidence
    g = links.sort_values("date_filed").groupby(["cusip", "cusip6", "subject_cik"]).agg(
        n_links=("accession", "size"), evidence_accession=("accession", "last"), evidence_date=("date_filed", "last"),
        company_name=("subject_name", "last"), form=("form_type", "last")).reset_index()
    per_cusip = g.groupby("cusip")["subject_cik"].nunique()
    conflict_cusips = per_cusip[per_cusip > 1]
    out.append(f"9-char CUSIPs mapping to >1 subject CIK: {len(conflict_cusips):,} / {len(per_cusip):,} = {len(conflict_cusips) / len(per_cusip):.2%}")
    # resolve a conflict by the CIK with most filings; flag it
    g["conflict_flag"] = g["cusip"].isin(conflict_cusips.index).astype(int)
    g = g.sort_values(["cusip", "n_links", "evidence_date"], ascending=[True, False, False])
    best = g.drop_duplicates("cusip").copy()
    # 6-char issuer level: classes of one issuer share the prefix
    per6 = best.groupby("cusip6")["subject_cik"].nunique()
    conf6 = per6[per6 > 1]
    out.append(f"6-char issuer prefixes mapping to >1 CIK (after 9-char resolution): {len(conf6):,} / {len(per6):,} = {len(conf6) / len(per6):.2%}")
    # 13F universe coverage + name agreement
    h = pd.read_parquet(f"cache/parsed/{label}_holdings.parquet", columns=["cusip", "cusip_status", "name_of_issuer", "put_call", "sh_prn"])
    sc = pd.read_parquet(f"cache/parsed/{label}_shares_check.parquet", columns=["cusip", "value_norm"])
    h = h[(h["put_call"] == "") & (h["sh_prn"] != "PRN") & h["cusip_status"].isin(["ok", "repaired_check_digit", "repaired_pad_zeros"])]
    names = h.groupby("cusip")["name_of_issuer"].agg(lambda s: s.value_counts().index[0])
    val6 = sc[sc["value_norm"] <= 2e8].groupby(sc["cusip"].str[:6])["value_norm"].sum()
    uni9 = pd.Index(h["cusip"].unique()); uni6 = pd.Index(h["cusip"].str[:6].unique())
    m9 = uni9.isin(best["cusip"]); m6 = uni6.isin(best["cusip6"])
    map6 = best.drop_duplicates("cusip6").set_index("cusip6")["subject_cik"]
    cov_val = val6.reindex(uni6).fillna(0)
    out.append(f"13F universe {label}: 9-char CUSIPs {len(uni9):,}, mapped directly {m9.sum():,} = {m9.mean():.1%}; "
               f"6-char issuers {len(uni6):,}, mapped via prefix {m6.sum():,} = {m6.mean():.1%}; "
               f"by 13F value: {cov_val[m6].sum() / cov_val.sum():.1%}")
    # name agreement on mapped 9-char CUSIPs: 13F issuer name vs EDGAR subject company name
    chk = best[best["cusip"].isin(uni9)].copy()
    chk["name_13f"] = chk["cusip"].map(names)
    def agree(a, b):
        ta, tb = norm_tokens(a), norm_tokens(b)
        if not ta or not tb:
            return None
        return len(ta & tb) / min(len(ta), len(tb)) >= 0.5 or (sorted(ta)[0][:5] == sorted(tb)[0][:5])
    chk["name_agree"] = [agree(a, b) for a, b in zip(chk["name_13f"], chk["company_name"])]
    ag = chk["name_agree"].dropna()
    out.append(f"name agreement (13F issuer name vs EDGAR subject name, token overlap >= 50% or same first word): {ag.sum():,} / {len(ag):,} = {ag.mean():.1%} on mapped 13F CUSIPs")
    dis = chk[chk["name_agree"] == False][["cusip", "name_13f", "company_name", "subject_cik", "n_links", "conflict_flag"]]  # noqa
    out.append("\nname disagreements (sample 25):\n" + dis.head(25).to_string(index=False, max_colwidth=34))
    out.append("\nconflicting CUSIPs (sample 15):\n" + g[g["conflict_flag"] == 1].head(15)[["cusip", "subject_cik", "company_name", "n_links", "evidence_accession"]].to_string(index=False, max_colwidth=34))
    Path("data").mkdir(exist_ok=True)
    best["company_cik"] = best["subject_cik"]; best["map_source"] = best["form"].str.replace("/A", "", regex=False)
    best["cusip9"] = best["cusip"]
    best[["cusip6", "cusip9", "company_cik", "company_name", "map_source", "evidence_accession", "evidence_date", "n_links", "conflict_flag"]].to_csv(f"data/{label}_cusip_cik_map.csv", index=False)
    chk.to_parquet(f"cache/parsed/{label}_cusip_cik_check.parquet", index=False)
    txt = "\n".join(out); Path(f"output/problems/{label}").mkdir(parents=True, exist_ok=True)
    open(f"output/problems/{label}/cusip_cik_validation.txt", "w").write(txt); print(txt)


if __name__ == "__main__":
    build(sys.argv[2], sys.argv[3])
