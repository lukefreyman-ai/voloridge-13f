"""Hand check: the N largest companies by 13F value in the ownership output, every input shown.
Usage: python3 scripts/hand_check.py <label> [N=20]   -> output/problems/<label>/hand_check.txt"""
import sys
import pandas as pd

label = sys.argv[1]; N = int(sys.argv[2]) if len(sys.argv) > 2 else 20
mc = pd.read_csv(f"output/{label}_institutional_ownership.csv", dtype={"cusip": str, "cusip_issuer": str})
mc["excluded_from_ownership"] = mc["excluded_from_ownership"].fillna(""); mc["over_100_cause"] = mc["over_100_cause"].fillna(""); mc["list_desc"] = mc["list_desc"].fillna("")
comp = pd.read_parquet(f"cache/parsed/{label}_ownership_company.parquet")
sc = pd.read_parquet(f"cache/parsed/{label}_shares_check.parquet", columns=["accession", "cusip", "value_norm", "median_price"])
sc = sc[sc["accession"].isin(mc["form_13f_accession_number"]) & (sc["value_norm"] <= 2e8)]
v9 = sc.groupby("cusip")["value_norm"].sum(); px = sc.groupby("cusip")["median_price"].first()
mc["value_k"] = mc["cusip"].map(v9)
vc = mc.drop_duplicates("cusip").groupby("company_cik")["value_k"].sum().sort_values(ascending=False)
so = pd.read_parquet(f"cache/parsed/{label}_shares_out.parquet")
f = pd.read_parquet(f"cache/parsed/{label}_filings.parquet")[["accession", "form_type", "filed_date", "amendment_type"]].set_index("accession")
out = [f"{label}: hand check of the {N} largest companies by 13F value (every input shown)\n"]
for cik in vc.head(N).index:
    xa = mc[mc["company_cik"] == cik]; x = xa[xa["excluded_from_ownership"] == ""]
    rr = comp[comp["company_cik"] == cik]
    r = rr.iloc[0] if len(rr) else pd.Series({"company_name": xa["company_name"].iloc[0], "shares_held_total": 0.0, "n_managers": 0, "shares_outstanding": float("nan"), "institutional_ownership_pct": float("nan"), "multi_class_flag": False})
    xe = xa[xa["excluded_from_ownership"] != ""]
    out.append("=" * 110)
    out.append(f"{xa['company_name'].iloc[0]}   CIK {int(cik)}   13F value ${vc[cik] / 1e6:,.1f}bn   map_source {xa['map_source'].iloc[0]}   conflict {int(xa['map_conflict'].fillna(0).max())}/{int(xa['map_conflict_two_sided'].fillna(0).max())}"
               + ("   [ALL ROWS EXCLUDED: " + ", ".join(sorted(set(xe["excluded_from_ownership"]))) + "]" if not len(x) else ""))
    cu = x.groupby("cusip").agg(managers=("manager_cik", "nunique"), filings=("form_13f_accession_number", "nunique"), shares=("shares_held", "sum"), value_k=("value_k", "first"), desc=("list_desc", "first"), class_shares_out=("class_shares_outstanding", "first"), class_pct=("class_ownership_pct", "first"), class_match=("class_match", "first"))
    cu["median_px"] = cu.index.map(px).astype(float).round(2)
    out.append("  CUSIPs held (counted):\n" + cu.to_string())
    if len(xe):
        ce = xe.groupby(["cusip", "excluded_from_ownership", "list_desc"]).agg(managers=("manager_cik", "nunique"), shares=("shares_held", "sum"))
        out.append("  CUSIPs EXCLUDED from the figure:\n" + ce.to_string())
    out.append(f"  shares held total {r['shares_held_total']:,.0f}  managers {r['n_managers']}  filings {x['form_13f_accession_number'].nunique()}  multi_filing rows {int(x['multi_filing_flag'].sum())}")
    s = so[so["cik"] == cik]
    out.append("  shares outstanding facts (XBRL, all rows for the CIK):\n" + (s[["class_axis", "shares", "form", "adsh", "shares_outstanding_date", "filed", "gap_days", "gap_flag"]].to_string(index=False) if len(s) else "    NONE"))
    out.append(f"  USED: shares_outstanding {r['shares_outstanding']:,.0f}  source {x['shares_outstanding_source'].iloc[0]}  as-of {x['shares_outstanding_date'].iloc[0]}  multi_class {bool(r['multi_class_flag'])}" if pd.notna(r["shares_outstanding"]) else "  USED: shares_outstanding NULL")
    out.append((f"  ==> institutional_ownership_pct = {r['shares_held_total']:,.0f} / {r['shares_outstanding']:,.0f} = {r['institutional_ownership_pct']:.2f}%" if pd.notna(r["institutional_ownership_pct"]) else "  ==> institutional_ownership_pct = NULL")
               + (f"   OVER 100: {x['over_100_cause'].iloc[0]}" if len(x) and x["over_100_flag"].iloc[0] else ""))
    top = x.sort_values("shares_held", ascending=False).head(5)[["manager_name", "manager_cik", "shares_held", "form_13f_accession_number"]].copy()
    top["form"] = top["form_13f_accession_number"].map(f["form_type"]); top["filed"] = top["form_13f_accession_number"].map(f["filed_date"])
    out.append("  top 5 holders:\n" + top.to_string(index=False, max_colwidth=36))
txt = "\n".join(out); open(f"output/problems/{label}/hand_check.txt", "w").write(txt); print(txt[:3000])
