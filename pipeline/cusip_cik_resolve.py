"""Stage 2 re-resolution of the CUSIP -> CIK map under the decisions of 2026-10-11.
  python3 -m pipeline.cusip_cik_resolve <label> <sc13_label> <quarter_end YYYY-MM-DD> <list_year> <list_qtr>
Decision 1 (conflicts): a 9-char CUSIP whose 13G/13D filings name more than one subject CIK is a conflict and is
  flagged (conflict_flag=1). The STOP-CONDITION rate uses the two-sided definition: >= 2 filings on each of >= 2 CIKs
  (conflict_two_sided=1). Resolution: majority CIK by filing count; for two-sided conflicts and 1-vs-1 ties
  (same company under two CIKs, typically), the CIK that filed a 10-K/10-Q (10-KT/10-QT) whose filing date is closest
  to the quarter end wins; CIK pairs are never merged. Every conflicted CUSIP and its candidate CIKs are logged in
  output/problems/<label>/conflict_pairs.csv.
Decision 3 (unmatched operating companies): exact normalized-name match from the SEC 13(f) list issuer name to EDGAR
  company names (full-index filers of 10-K/10-Q/20-F/40-F and 1940-Act forms). Normalization = upper, & -> AND,
  punctuation out, EDGAR '/DE/'-style suffixes out, CUSIP-standard abbreviations applied to both sides, single-letter
  runs joined (A G -> AG), trailing corporate-form tokens dropped (INC CORP CO LTD PLC LLC LP SA NV AG NEW DEL).
  A match needs exactly one CIK; names normalizing to several CIKs and fuzzy candidates go to
  data/<label>_name_match_review.csv only. Validation: the same rule applied to issuers already mapped by 13G/13D,
  agreement rate reported. Added rows carry map_source='name_exact'.
Output: data/<label>_cusip_cik_map.csv (v1 kept as *_v1.csv), output/problems/<label>/cusip_cik_resolution.txt."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .cusip import is_valid9
from . import funds as fundsmod

ISSUER_FORMS = ("10-K", "10-Q", "10-KT", "10-QT", "20-F", "40-F")
FUND_FORMS = re.compile(r"^(N-CSR|N-Q|N-30D|485BPOS|24F-2NT|NSAR-B)")
ABBR = {"CORPORATION": "CORP", "INCORPORATED": "INC", "COMPANY": "CO", "COMPANIES": "COS", "LIMITED": "LTD",
        "HOLDINGS": "HLDGS", "HOLDING": "HLDG", "INTERNATIONAL": "INTL", "FINANCIAL": "FINL", "GROUP": "GRP",
        "INDUSTRIES": "INDS", "INDUSTRIAL": "INDL", "SERVICES": "SVCS", "SERVICE": "SVC", "TECHNOLOGIES": "TECH",
        "TECHNOLOGY": "TECH", "SYSTEMS": "SYS", "SYSTEM": "SYS", "BANK": "BK", "BANCORPORATION": "BANCORP",
        "PROPERTIES": "PPTYS", "PROPERTY": "PPTY", "REALTY": "RLTY", "TRUST": "TR", "RESOURCES": "RES",
        "MANAGEMENT": "MGMT", "NATIONAL": "NATL", "AMERICAN": "AMERN", "AMERICA": "AMER", "ASSOCIATES": "ASSOC",
        "ASSOCIATION": "ASSN", "INVESTMENT": "INVT", "INVESTMENTS": "INVTS", "INVESTORS": "INVS", "MEDICAL": "MED",
        "PETROLEUM": "PETE", "ELECTRIC": "ELEC", "ELECTRONICS": "ELECTRS", "EQUIPMENT": "EQUIP",
        "MANUFACTURING": "MFG", "PRODUCTS": "PRODS", "INSURANCE": "INS", "SAVINGS": "SVGS", "FEDERAL": "FED",
        "LABORATORIES": "LABS", "CAPITAL": "CAP", "SECURITIES": "SECS", "DEVELOPMENT": "DEV", "GENERAL": "GEN",
        "CONSOLIDATED": "CONS", "COMMUNICATIONS": "COMMUNICATIONS", "RAILWAY": "RY", "RAILROAD": "RR",
        "MOTORS": "MTRS", "STORES": "STRS", "PHARMACEUTICALS": "PHARMACEUTICALS", "ENTERPRISES": "ENTERPRISES",
        "PUBLIC": "PUB", "RESTAURANTS": "RESTAURANTS", "MACHINES": "MACHS", "MACHINE": "MACH", "PARTNERS": "PARTNERS",
        "ENERGY": "ENERGY", "HEALTHCARE": "HEALTHCARE", "ENTERTAINMENT": "ENTMT", "COMMERCIAL": "COML",
        "DEPARTMENT": "DEPT", "MARKETING": "MKTG", "MARKETS": "MKTS", "MARKET": "MKT", "BROADCASTING": "BRDCSTG",
        "MINING": "MNG", "CHEMICALS": "CHEMS", "CHEMICAL": "CHEM", "AIRLINES": "AIRLS", "TRANSPORTATION": "TRANS"}
SUFFIX = {"INC", "CORP", "CO", "LTD", "PLC", "LLC", "LP", "SA", "NV", "AG", "NEW", "DEL", "SE", "SPA", "PUBLTDCO", "PUBLTD"}
STOP_LEAD = {"THE"}


def norm_name(name: str) -> str:
    s = (name or "").upper()
    s = re.sub(r"\(.*?\)", " ", s)                       # (formerly ...)
    s = re.sub(r"\bFORMERLY\b.*$", " ", s)
    s = re.sub(r"/[A-Z0-9 .&'-]*/?\s*$", " ", s)         # EDGAR /DE/ , /NY , /NEW/
    s = s.replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    toks = [ABBR.get(t, t) for t in s.split()]
    # join runs of single letters: A G -> AG, L P -> LP, E M C -> EMC
    out, run = [], False
    for t in toks:
        if len(t) == 1 and t.isalpha():
            if run:
                out[-1] += t
            else:
                out.append(t); run = True
        else:
            out.append(t); run = False
    toks = out
    if toks and toks[0] in STOP_LEAD:
        toks = toks[1:]
    s2 = " ".join(toks).replace("PUB LTD CO", "PLC").replace("PUB LIMITED CO", "PLC")
    toks = s2.split()
    while toks and (toks[-1] in SUFFIX or toks[-1] == "AND"):
        toks.pop()
    return " ".join(toks)


def tenk_filings(idx: pd.DataFrame) -> pd.DataFrame:
    t = idx[idx["form_type"].isin(("10-K", "10-Q", "10-KT", "10-QT"))].copy()
    t["date_filed"] = pd.to_datetime(t["date_filed"])
    return t


def resolve(label: str, sc13_label: str, qend: str, ly: int, lq: int):
    qe = pd.Timestamp(qend)
    out = [f"{label}: CUSIP->CIK resolution v2 (decisions 2026-10-11), quarter end {qend}, 13(f) list {ly}q{lq}"]
    links = pd.read_parquet(f"cache/parsed/{sc13_label}_sc13_links.parquet")
    links = links[links["cusip"].notna() & links["subject_cik"].notna()].copy()
    links["cusip"] = links["cusip"].str.upper()
    links = links[(links["cusip"].str.len() == 9) & links["cusip"].map(is_valid9)]
    n_placeholder = (links["cusip"] == "000000000").sum()
    links = links[links["cusip"] != "000000000"]          # placeholder CUSIP on 13G cover pages: not a security
    links["cusip6"] = links["cusip"].str[:6]
    links["subject_cik"] = links["subject_cik"].astype(int)
    g = links.sort_values("date_filed").groupby(["cusip", "cusip6", "subject_cik"]).agg(
        n_links=("accession", "size"), evidence_accession=("accession", "last"), evidence_date=("date_filed", "last"),
        company_name=("subject_name", "last"), form=("form_type", "last")).reset_index()
    n_ciks = g.groupby("cusip")["subject_cik"].transform("nunique")
    g["conflict_flag"] = (n_ciks > 1).astype(int)
    strong = g[g["n_links"] >= 2].groupby("cusip")["subject_cik"].nunique()
    two_sided = set(strong[strong >= 2].index)
    g["conflict_two_sided"] = g["cusip"].isin(two_sided).astype(int)
    top2 = g.sort_values(["cusip", "n_links"], ascending=[True, False]).groupby("cusip")["n_links"].apply(lambda s: s.iloc[0] == s.iloc[1] if len(s) > 1 else False)
    g["tie"] = g["cusip"].map(top2).fillna(False).astype(bool)
    # 10-K/10-Q closest to quarter end, per CIK (EDGAR full index 2010Q1-2015Q1, originals only)
    idx = pd.read_parquet("cache/parsed/edgar_full_index_2010Q1_2015Q1.parquet")
    tk = tenk_filings(idx)
    tk["gap"] = (tk["date_filed"] - qe).dt.days.abs()
    tk = tk.sort_values("gap").drop_duplicates("cik")
    g["tenk_date"] = g["subject_cik"].map(tk.set_index("cik")["date_filed"])
    g["tenk_gap"] = g["subject_cik"].map(tk.set_index("cik")["gap"])
    g["tenk_accession"] = g["subject_cik"].map(tk.set_index("cik")["accession"])
    # resolution
    g["rule"] = "single CIK"
    g.loc[g["conflict_flag"] == 1, "rule"] = "conflict: majority by filing count"
    use_tenk = (g["conflict_two_sided"] == 1) | ((g["conflict_flag"] == 1) & g["tie"])
    has_tenk = g["cusip"].isin(g.loc[use_tenk & g["tenk_gap"].notna() & (g["tenk_gap"] <= 400), "cusip"])
    g.loc[use_tenk & has_tenk, "rule"] = "two-sided/tie: CIK with 10-K/10-Q filed closest to quarter end"
    g.loc[use_tenk & ~has_tenk, "rule"] = "two-sided/tie: no 10-K/10-Q within 400 days, majority / latest evidence"
    g["_tenk_sort"] = np.where(use_tenk & has_tenk, g["tenk_gap"].fillna(9e9), 0)
    g = g.sort_values(["cusip", "_tenk_sort", "n_links", "evidence_date"], ascending=[True, True, False, False])
    g["chosen"] = ~g.duplicated("cusip")
    pairs = g[g["conflict_flag"] == 1][["cusip", "subject_cik", "company_name", "n_links", "evidence_accession", "conflict_two_sided", "tie", "tenk_date", "tenk_gap", "rule", "chosen"]]
    Path(f"output/problems/{label}").mkdir(parents=True, exist_ok=True)
    pairs.to_csv(f"output/problems/{label}/conflict_pairs.csv", index=False)
    n_valid = g["cusip"].nunique(); n_raw = g.loc[g["conflict_flag"] == 1, "cusip"].nunique(); n_two = len(two_sided)
    out.append(f"valid 9-char CUSIPs with a subject CIK: {n_valid:,} (placeholder 000000000 dropped from {n_placeholder} filings)")
    out.append(f"conflicts, raw definition (>1 subject CIK): {n_raw:,} = {n_raw / n_valid:.2%}  -> all flagged conflict_flag=1")
    out.append(f"conflicts, TWO-SIDED definition (>=2 filings on each of >=2 CIKs): {n_two:,} = {n_two / n_valid:.2%}   [stop condition 2%: {'HIT' if n_two / n_valid > 0.02 else 'not hit'}]")
    ties = g[(g['conflict_flag'] == 1) & g['tie']]['cusip'].nunique()
    out.append(f"1-vs-1 ties among raw conflicts: {ties:,}; two-sided or tie resolved by 10-K/10-Q closeness: {g.loc[g['rule'].str.startswith('two-sided/tie: CIK'), 'cusip'].nunique():,}; "
               f"with no 10-K/10-Q in reach (majority kept): {g.loc[g['rule'].str.startswith('two-sided/tie: no'), 'cusip'].nunique():,}")
    chosen = g[g["chosen"]].copy()
    flipped = chosen[(chosen["rule"].str.startswith("two-sided/tie: CIK"))].merge(
        g.sort_values(["cusip", "n_links"], ascending=[True, False]).drop_duplicates("cusip")[["cusip", "subject_cik"]].rename(columns={"subject_cik": "majority_cik"}), on="cusip")
    flipped = flipped[flipped["subject_cik"] != flipped["majority_cik"]]
    out.append(f"CUSIPs where the 10-K/10-Q rule chose a CIK other than the majority: {len(flipped):,}")
    out.append("two-sided conflicts (all, by filing count):\n" + pairs[pairs["conflict_two_sided"] == 1].sort_values(["cusip", "n_links"], ascending=[True, False])
               [["cusip", "subject_cik", "company_name", "n_links", "tenk_date", "tenk_gap", "chosen"]].to_string(index=False, max_colwidth=34))
    best = chosen.rename(columns={"subject_cik": "company_cik"})
    best["map_source"] = best["form"].str.replace("/A", "", regex=False)
    best["cusip9"] = best["cusip"]
    best["evidence"] = ""
    cols = ["cusip6", "cusip9", "company_cik", "company_name", "map_source", "evidence_accession", "evidence_date", "n_links", "conflict_flag", "conflict_two_sided", "rule", "evidence"]
    best = best[cols]

    # ---------- decision 3: exact normalized name match for unmapped issuers
    sl = pd.read_parquet(f"cache/parsed/seclist_{ly}q{lq}.parquet")
    sl_nonopt = sl[~sl["issuer_desc"].isin(["CALL", "PUT"])]
    list_name = sl_nonopt.groupby("cusip6")["issuer_name"].agg(lambda s: s.value_counts().index[0])
    h = pd.read_parquet(f"cache/parsed/{label}_holdings.parquet", columns=["cusip", "cusip_status", "put_call", "sh_prn"])
    h = h[(h["put_call"] == "") & (h["sh_prn"] != "PRN") & h["cusip_status"].isin(["ok", "repaired_check_digit", "repaired_pad_zeros"])]
    sc = pd.read_parquet(f"cache/parsed/{label}_shares_check.parquet", columns=["cusip", "value_norm"])
    val6 = sc[sc["value_norm"] <= 2e8].groupby(sc["cusip"].str[:6])["value_norm"].sum()
    uni6 = pd.Index(h["cusip"].str[:6].unique())
    val6 = val6.reindex(uni6).fillna(0)
    # EDGAR issuer names: filers of 10-K/10-Q/20-F/40-F or 1940-Act report forms
    ed = idx[idx["form_type"].isin(ISSUER_FORMS) | idx["form_type"].str.match(FUND_FORMS)].copy()
    ed["date_filed"] = pd.to_datetime(ed["date_filed"]); ed["gap"] = (ed["date_filed"] - qe).dt.days.abs()
    ed_ev = ed.sort_values("gap").drop_duplicates("cik").set_index("cik")
    names = ed[["cik", "company_name"]].drop_duplicates()
    names["norm"] = names["company_name"].map(norm_name)
    names = names[names["norm"] != ""]
    nmap = names.groupby("norm")["cik"].agg(lambda s: sorted(set(s)))
    norm_to_ciks = nmap.to_dict()
    # validation on issuers already mapped by 13G/13D
    mapped6 = best.drop_duplicates("cusip6").set_index("cusip6")["company_cik"]
    v_rows = []
    for c6, cik in mapped6.items():
        ln = list_name.get(c6)
        if ln is None:
            continue
        cands = norm_to_ciks.get(norm_name(ln))
        if cands and len(cands) == 1:
            v_rows.append((c6, cik, cands[0]))
    v = pd.DataFrame(v_rows, columns=["cusip6", "cik_13g", "cik_name"])
    agree = (v["cik_13g"] == v["cik_name"]).mean() if len(v) else float("nan")
    out.append(f"\nname match validation on issuers mapped by 13G/13D with a 13(f) list name: exact unique matches {len(v):,} / {len(mapped6):,}; "
               f"agreement with the 13G/13D CIK {(v['cik_13g'] == v['cik_name']).sum():,} / {len(v):,} = {agree:.1%}")
    dis = v[v["cik_13g"] != v["cik_name"]].copy()
    dis["list_name"] = dis["cusip6"].map(list_name); dis["name_13g"] = dis["cik_13g"].map(ed_ev["company_name"]); dis["name_match"] = dis["cik_name"].map(ed_ev["company_name"])
    out.append("disagreements (sample 15):\n" + dis.head(15).to_string(index=False, max_colwidth=30))
    # apply to unmapped issuers
    unm = uni6[~uni6.isin(best["cusip6"])]
    add, review = [], []
    tok_index = {}
    for n, cs in norm_to_ciks.items():
        for t in set(n.split()):
            tok_index.setdefault(t, set()).add(n)
    for c6 in unm:
        ln = list_name.get(c6)
        if ln is None:
            continue
        nn = norm_name(ln)
        cands = norm_to_ciks.get(nn)
        if cands and len(cands) == 1:
            cik = cands[0]
            ev = ed_ev.loc[cik] if cik in ed_ev.index else None
            add.append({"cusip6": c6, "cusip9": "", "company_cik": cik, "company_name": ev["company_name"] if ev is not None else "", "map_source": "name_exact",
                        "evidence_accession": ev["accession"] if ev is not None else "", "evidence_date": ev["date_filed"].strftime("%Y-%m-%d") if ev is not None else "",
                        "n_links": 0, "conflict_flag": 0, "conflict_two_sided": 0, "rule": "exact normalized name", "evidence": f"13(f) list '{ln}' == EDGAR '{nn}'"})
        elif cands:
            review.append({"cusip6": c6, "list_name": ln, "norm": nn, "reason": f"ambiguous: {len(cands)} CIKs", "candidates": "|".join(f"{c}:{ed_ev['company_name'].get(c, '')}" for c in cands[:5]), "value_k": val6.get(c6, 0)})
        else:
            toks = set(nn.split())
            if not toks:
                continue
            pool = set().union(*(tok_index.get(t, set()) for t in toks))
            scored = []
            for cand in pool:
                ct = set(cand.split()); j = len(toks & ct) / len(toks | ct)
                if j >= 0.5:
                    scored.append((j, cand))
            scored.sort(reverse=True)
            if scored:
                review.append({"cusip6": c6, "list_name": ln, "norm": nn, "reason": "fuzzy (token Jaccard >= 0.5)",
                               "candidates": "|".join(f"{j:.2f} {cand} -> {','.join(map(str, norm_to_ciks[cand][:3]))}" for j, cand in scored[:3]), "value_k": val6.get(c6, 0)})
    addf = pd.DataFrame(add, columns=cols)
    rev = pd.DataFrame(review).sort_values("value_k", ascending=False) if review else pd.DataFrame(columns=["cusip6", "list_name", "norm", "reason", "candidates", "value_k"])
    rev.to_csv(f"data/{label}_name_match_review.csv", index=False)
    fund = fundsmod.load().set_index("cik")["reason"]
    addf["is_fund"] = addf["company_cik"].map(fund).notna()
    in_list = unm.isin(list_name.index)
    out.append(f"\nunmapped 13F issuers (6-char): {len(unm):,} carrying ${val6[unm].sum() / 1e6:,.1f}bn; with a 13(f) list name: {in_list.sum():,} (${val6[unm[in_list]].sum() / 1e6:,.1f}bn)")
    out.append(f"exact unique name matches added: {len(addf):,} issuers = ${val6.reindex(addf['cusip6']).sum() / 1e6:,.1f}bn; of these fund CIKs (excluded later): {addf['is_fund'].sum():,} = ${val6.reindex(addf.loc[addf['is_fund'], 'cusip6']).sum() / 1e6:,.1f}bn")
    out.append(f"review file (ambiguous + fuzzy, NOT used): {len(rev):,} rows = ${rev['value_k'].sum() / 1e6:,.1f}bn -> data/{label}_name_match_review.csv; by reason: {rev['reason'].value_counts().to_dict() if len(rev) else {}}")
    tot = val6.sum()
    out.append(f"coverage of 13F value, all issuers: 13G/13D map {val6[uni6.isin(best['cusip6'])].sum() / tot:.1%} -> with name matches {val6[uni6.isin(best['cusip6']) | uni6.isin(addf['cusip6'])].sum() / tot:.1%}")
    out.append("largest name-match additions:\n" + addf.assign(value_bn=(val6.reindex(addf["cusip6"]).values / 1e6).round(2)).sort_values("value_bn", ascending=False).head(25)[["cusip6", "company_cik", "company_name", "is_fund", "value_bn", "evidence"]].to_string(index=False, max_colwidth=40))
    out.append("largest review-file rows (not used):\n" + rev.head(15)[["cusip6", "list_name", "reason", "candidates", "value_k"]].to_string(index=False, max_colwidth=48))
    final = pd.concat([best, addf.drop(columns=["is_fund"])], ignore_index=True)
    final = final.sort_values(["cusip6", "n_links", "cusip9"], ascending=[True, False, True])
    v1 = Path(f"data/{label}_cusip_cik_map_v1.csv")
    if not v1.exists() and Path(f"data/{label}_cusip_cik_map.csv").exists():      # pilots had a v1 map; new quarters do not
        Path(f"data/{label}_cusip_cik_map.csv").rename(v1)
    final.to_csv(f"data/{label}_cusip_cik_map.csv", index=False)
    txt = "\n".join(out)
    open(f"output/problems/{label}/cusip_cik_resolution.txt", "w").write(txt); print(txt)


if __name__ == "__main__":
    resolve(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
