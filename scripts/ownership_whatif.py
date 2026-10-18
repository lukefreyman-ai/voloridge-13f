"""Read-only what-if for the Stage 4 stop condition (top-500 over-100% rate). No output is changed.
Scenarios stack:  S0 as produced | S1 exclude debt-pattern CUSIPs (letter in CUSIP position 7 = fixed-income issue
number) filed as SH | S2 + collapse 13F-HR/A 'NEW HOLDINGS' amendments that duplicate the original (>= 90% of the
original's CUSIPs repeated with identical shares) | S3 + null ADR/ADS securities (13(f) list description) whose dei
share count is in ordinary shares.  Usage: python3 scripts/ownership_whatif.py <label> <quarter_end>"""
import sys
import numpy as np
import pandas as pd

label, qend = sys.argv[1], sys.argv[2]
qe = pd.Timestamp(qend); ly, lq = qe.year, (qe.month - 1) // 3 + 1
mc = pd.read_csv(f"output/{label}_institutional_ownership.csv", dtype={"cusip": str, "cusip_issuer": str})
f = pd.read_parquet(f"cache/parsed/{label}_filings.parquet").set_index("accession")
sl = pd.read_parquet(f"cache/parsed/seclist_{ly}q{lq}.parquet").drop_duplicates("cusip").set_index("cusip")
sc = pd.read_parquet(f"cache/parsed/{label}_shares_check.parquet", columns=["accession", "cusip", "value_norm"])
sc = sc[sc["accession"].isin(mc["form_13f_accession_number"]) & (sc["value_norm"] <= 2e8)]
v9 = sc.groupby("cusip")["value_norm"].sum()
mc["value_k"] = mc["cusip"].map(v9).fillna(0)
mc["debt_cusip"] = mc["cusip"].str[6].str.isalpha()
mc["list_desc"] = mc["cusip"].map(sl["issuer_desc"]).fillna("(not in 13(f) list)")
mc["adr"] = mc["list_desc"].str.contains(r"\bADR|\bADS|SPON ADR|SP ADR", regex=True)
mc["form"] = mc["form_13f_accession_number"].map(f["form_type"]); mc["atype"] = mc["form_13f_accession_number"].map(f["amendment_type"]).fillna("")
# duplicate NEW HOLDINGS amendments
dup_amend = []
for cik, g in mc[mc["manager_cik"].isin(mc.groupby("manager_cik")["form_13f_accession_number"].nunique().loc[lambda s: s > 1].index)].groupby("manager_cik"):
    orig = g[g["form"] == "13F-HR"]; am = g[(g["form"] == "13F-HR/A")]
    if not len(orig) or not len(am):
        continue
    o = orig.set_index("cusip")["shares_held"]
    for acc, a in am.groupby("form_13f_accession_number"):
        same = (a.set_index("cusip")["shares_held"].reindex(o.index) == o).sum()
        if same >= 0.9 * len(o):
            dup_amend.append((acc, cik, a["atype"].iloc[0], len(o), len(a), int(same)))
dup = pd.DataFrame(dup_amend, columns=["accession", "manager_cik", "atype", "orig_rows", "amend_rows", "identical"])
out = [f"{label}: what-if on the over-100% stop condition (read-only; output unchanged)",
       f"debt-pattern CUSIPs filed as SH: {mc['debt_cusip'].sum():,} rows, {mc.loc[mc['debt_cusip'], 'cusip'].nunique():,} CUSIPs, ${mc.loc[mc['debt_cusip']].drop_duplicates('cusip')['value_k'].sum() / 1e6:,.1f}bn; "
       f"13(f) list descriptions of those: {mc.loc[mc['debt_cusip']].drop_duplicates('cusip')['list_desc'].str.slice(0, 6).value_counts().head(6).to_dict()}",
       f"13(f) list description of ALL output CUSIPs (distinct), top: {mc.drop_duplicates('cusip')['list_desc'].str.split().str[0].value_counts().head(10).to_dict()}",
       f"ADR/ADS CUSIPs in output: {mc.loc[mc['adr'], 'cusip'].nunique():,} on {mc.loc[mc['adr'], 'company_cik'].nunique():,} companies, ${mc.loc[mc['adr']].drop_duplicates('cusip')['value_k'].sum() / 1e6:,.1f}bn",
       f"amendments duplicating the original (>= 90% identical rows): {len(dup):,} ({dup['atype'].value_counts().to_dict() if len(dup) else {}}), rows {dup['amend_rows'].sum() if len(dup) else 0:,}",
       (dup.merge(f[["manager_name"]], left_on="accession", right_index=True).to_string(index=False, max_colwidth=36) if len(dup) else "")]
vcik = mc.drop_duplicates("cusip").groupby("company_cik")["value_k"].sum(); top500 = set(vcik.sort_values(ascending=False).head(500).index)
def scen(d, name):
    comp = d.groupby("company_cik").agg(held=("shares_held", "sum"), so=("shares_outstanding", "first"), mcf=("multi_class_flag", "max"), adr=("adr", "max"))
    pct = np.where(comp["mcf"], np.nan, comp["held"] / comp["so"] * 100)
    comp["pct"] = pct
    p = comp["pct"].dropna(); big = comp[comp.index.isin(top500)]["pct"].dropna()
    out.append(f"{name:60} all: over 100% {int((p > 100).sum()):5,} / {len(p):5,} = {(p > 100).mean():5.1%} | median {p.median():5.1f} | top-500: {int((big > 100).sum()):3} / {len(big)} = {(big > 100).mean():5.1%}")
    return comp
scen(mc, "S0 as produced")
s1 = mc[~mc["debt_cusip"]]; scen(s1, "S1 drop debt-pattern CUSIPs")
s2 = s1[~s1["form_13f_accession_number"].isin(dup["accession"])] if len(dup) else s1; scen(s2, "S2 + collapse duplicate amendments")
s3 = s2[~s2["adr"]]; comp3 = scen(s3, "S3 + drop ADR/ADS securities")
rem = comp3[(comp3["pct"] > 100) & comp3.index.isin(top500)].sort_values("pct", ascending=False)
rem["name"] = rem.index.map(mc.drop_duplicates("company_cik").set_index("company_cik")["company_name"])
rem["value_bn"] = (vcik.reindex(rem.index) / 1e6).round(1)
rem["n_cusips"] = rem.index.map(s3.groupby("company_cik")["cusip"].nunique())
rem["so_date"] = rem.index.map(mc.drop_duplicates("company_cik").set_index("company_cik")["shares_outstanding_date"])
rem["so_source"] = rem.index.map(mc.drop_duplicates("company_cik").set_index("company_cik")["shares_outstanding_source"])
out.append(f"\nremaining top-500 companies over 100% under S3: {len(rem)}\n" + rem[["name", "held", "so", "pct", "value_bn", "n_cusips", "so_date", "so_source"]].round(1).to_string(max_colwidth=30))
txt = "\n".join(out); open(f"output/problems/{label}/ownership_whatif.txt", "w").write(txt); print(txt)
