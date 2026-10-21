"""Stage 4: institutional ownership per company-quarter for one pilot.
  python3 -m pipeline.ownership <label> <quarter_end YYYY-MM-DD> <period_of_report YYYYMMDD>
Inputs: <label>_holdings/_filings parquets, data/<label>_cusip_cik_map.csv (v2: 13G/13D + exact-name rows),
<label>_shares_out.parquet (XBRL), optional <label>_shares_out_regex.parquet (only exists if the regex fallback was
approved and deployed), cache/parsed/fund_ciks.parquet, cache/parsed/seclist_<y>q<q>.parquet.
Rules: SH rows only, no put/call, resolved CUSIPs only;
period_of_report == the pilot period; 13F-HR/A RESTATEMENT replaces the manager's original for the
period, NEW HOLDINGS appends, unknown amendment type -> treated as RESTATEMENT when an original exists
(logged); duplicate filings by the same manager for the same period: latest filed wins; duplicate CUSIP
rows within a filing are summed. Company pct = sum of shares across the issuer's CUSIPs / a denominator that covers
exactly those CUSIPs' share classes (decision 15 below), null with a stated cause when no such denominator exists.
Decision 2 (2026-10-11): ETFs, closed-end funds and unit trusts are EXCLUDED from the ownership output
(pipeline/funds.py: F1 1940-Act/UIT forms, F2 SIC 6221 commodity trusts, F3 13(f) list ETF/ETN rows); the removed
CUSIPs and value are reported, and issuer coverage is reported among operating companies only.
Luke 2026-10-12 (after the over-100% stop): (i) debt-pattern CUSIPs (letter in CUSIP position 7) filed as SH are
flagged and EXCLUDED from the ownership figure, rows kept (excluded_from_ownership='debt_cusip'); (ii) a 13F-HR/A
"NEW HOLDINGS" amendment that repeats >= 90% of the original's rows with identical shares is treated as a RESTATEMENT
(the original's rows are dropped, count reported); (iii) ADR/ADS securities (13(f) list description) are flagged and
excluded from the main figure (excluded_from_ownership='adr'), count and value reported. Remaining over-100% companies
are reported with causes and flagged in the output (over_100_flag, over_100_cause; 'no identified data cause' when none
applies, with securities lending named in the write-up only); no further tuning toward 5%.
Share classes (Luke 2026-10-12, decision 3): class share counts are NEVER summed into a denominator that does not
cover them. Each CUSIP gets class_ownership_pct against its own class's share count when the 13(f) list class (CL A/B/C)
matches an XBRL class member.
Decision 15 (2026-10-21), after pipeline/continuity.py measured 133 published figures between 100% and 296% whose
denominator covered one class while the numerator summed two: the company figure now rests on a denominator that covers
exactly the classes held, and company_denominator() records which basis on every row (denominator_basis):
  single_class_held     one class held and the company total is known: the company total is the denominator, which is
                        the definition the spec asks for (Nike 2013Q3 is 67.6% of all shares, not 84.4% of its CL B)
  single_class_matched  one class held and the undimensioned count is SMALLER than that class, so it cannot be the
                        total (Triple-S Management 2013Q3), or there is no undimensioned count at all
  classes_combined      more than one class held and every one has a count: they are summed (Central Garden & Pet)
  undimensioned_total   the undimensioned count agrees with the class facts' sum, so it already includes them
  incomplete/ambiguous  no figure, and pct_suppressed_cause names which class is missing or that coverage cannot be read
Decision 15b: three security types that are not the common stock they were divided by leave the figure (rows kept and
flagged, as with ADR and debt): warrants and rights, dated SPAC units ("UNIT 99/99/9999"), and preferred. Undated units
("COM UNIT LP", "UNIT LTD PARTN") are the equity of a partnership or trust and stay in.
Value is never used for the metric; value_scale_flag is carried as information only."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import funds as fundsmod

REQUIRED = ["quarter_end", "company_name", "company_cik", "cusip", "manager_cik", "manager_name", "shares_held",
            "shares_outstanding", "institutional_ownership_pct", "form_13f_accession_number",
            "shares_outstanding_source", "shares_outstanding_date"]
TRACEABILITY = ["shares_outstanding_evidence", "cusip_issuer", "map_source", "list_desc", "excluded_from_ownership",
                "class_shares_outstanding", "class_ownership_pct", "class_match", "multi_class_flag", "map_conflict",
                "company_shares_outstanding", "denominator_basis",
                "map_conflict_two_sided", "multi_filing_flag", "dup_amendment_flag", "debt_cusip_flag", "adr_flag",
                "over_100_flag", "over_100_cause", "n_rows", "pct_suppressed_cause", "n_source_filings"]
OUTPUT_COLUMNS = REQUIRED + TRACEABILITY


def output_path(label: str) -> Path:
    return Path("output") / f"{label}_institutional_ownership.csv"


# Decision 15 (2026-10-21): the numerator and the denominator must cover the SAME share classes.
# The defect this fixes, found by pipeline/continuity.py: decision 3 nulls the company figure when a
# company reports class-dimensioned facts ONLY. A filer that reports an undimensioned count AND
# class-dimensioned counts failed that test, so its figure was published - with holdings summed
# across every class the institutions held, over a denominator covering one of them. Central Garden
# & Pet 2013Q2 published 296.1%: holdings of 36,257,911 across its COM and CL A CUSIPs over an
# undimensioned count of 12,246,751, while its own Class A fact that quarter was 35,321,862.
# 133 published figures between 100% and 296% were this, on 60 companies.
#
# The classes a company's institutions actually hold are known from the SEC's own 13(f) list
# (issuer_desc: COM, CL A, CL B), so coverage is checkable rather than assumed.
CLASS_TOTAL_TOL = 0.95     # an undimensioned count within 5% of the class facts' sum IS the total


def company_denominator(und, held_keys, class_counts, class_facts_sum):
    """The denominator for one company-quarter, and the basis it rests on.

    und            the undimensioned share count, or None
    held_keys      the distinct 13(f) classes the institutions hold: 'COM' plus letters, e.g. {'COM','A'}
    class_counts   letter -> that class's XBRL share count
    class_facts_sum  the company's class-dimensioned facts, deduplicated (one per letter, plus the
                     largest unlettered one), summed. Used only to ask whether `und` is the total.

    Returns (denominator, basis, cause). A null denominator always carries a cause.
    """
    if len(held_keys) <= 1:
        # One class held, and the question is only whether the undimensioned count can be the
        # company total. It cannot be if it is SMALLER than the single class being held.
        key = next(iter(held_keys), "COM")
        own_class = class_counts.get(key) if key != "COM" else None
        if own_class is not None and (und is None or und < own_class):
            # The undimensioned count is SMALLER than the single class being held, so it cannot be
            # the company total. The held class's own count is then the only denominator that
            # covers the numerator.
            return (own_class, "single_class_matched", "")
        # Otherwise keep the undimensioned count. This is deliberate and it is a definition, not a
        # fallback: institutional ownership here is of the COMPANY, so when a company's total is
        # known it stays the denominator even though institutions only hold one of its classes.
        # Nike is the case: institutions hold its CL B (654106103), and 2013Q3 gives 67.6% of all
        # 889,555,117 shares or 84.4% of the 711,597,241 Class B shares. Both are true statements;
        # the spec asks for ownership per company, so the company total wins, and the per-class
        # figure is published alongside it in class_ownership_pct.
        return (und, "single_class_held", "" if und is not None else "no_shares_outstanding")
    counts = {k: (und if k == "COM" else class_counts.get(k)) for k in held_keys}
    missing = sorted(k for k, v in counts.items() if v is None)
    if missing:
        # no count for a class whose holdings are in the numerator: nothing honest to divide by
        return (None, "incomplete", "class_denominator_missing:" + ",".join(missing))
    # Is `und` already the total of the classes? Only if it AGREES with their sum, which is a
    # two-sided test. Written one-sided (und >= 0.95 * sum) it was satisfied by any count merely
    # larger than the class facts, so a company reporting 80m undimensioned against a single 20m
    # Class A fact was called a total when it is just as likely to be one untagged class.
    if und is not None and class_facts_sum and \
            CLASS_TOTAL_TOL * class_facts_sum <= und <= class_facts_sum / CLASS_TOTAL_TOL:
        # the filer tagged the total as well as the classes, so the classes are already inside it
        return (und, "undimensioned_total", "")
    letters = sum(v for k, v in counts.items() if k != "COM")
    if und is not None and letters and und >= letters and not (class_facts_sum and class_facts_sum > und):
        # und exceeds every class fact we have, and the class facts do not account for it: it could
        # be the company total or it could be one large class, and the data cannot say which.
        # Publishing either reading would be a guess, so this is reported, not published.
        return (None, "ambiguous", "denominator_coverage_ambiguous")
    return (sum(counts.values()), "classes_combined", "")


def write_output(mc: pd.DataFrame, label: str) -> Path:
    """Write the per-quarter deliverable: the 12 spec columns first, then the traceability columns."""
    Path("output").mkdir(exist_ok=True)
    # the stated grain is one row per manager x security x quarter: enforce it rather than claim it
    # CIKs and share counts are integers: "732717.0" breaks every join a consumer attempts
    for col, typ in (("company_cik", "Int64"), ("manager_cik", "Int64"),
                     ("shares_held", "Int64"), ("shares_outstanding", "Int64"),
                     ("company_shares_outstanding", "Int64")):
        if col in mc:
            mc[col] = pd.to_numeric(mc[col], errors="coerce").round().astype(typ)
    dup = mc.duplicated(["cusip", "manager_cik"], keep=False)
    if dup.any():
        ex = mc.loc[dup, ["manager_name", "cusip", "shares_held"]].head(6).to_string(index=False)
        raise ValueError(f"{label}: {int(dup.sum())} duplicate (cusip, manager_cik) rows would be "
                         f"published, which double counts holdings. Examples:\n{ex}")
    p = output_path(label)
    mc[OUTPUT_COLUMNS].to_csv(p, index=False)
    return p


# decision 12 thresholds: a US listed company with 13F holders has more than a thousand shares
# outstanding and fewer than a hundred billion. Outside that the XBRL fact is a unit error.
MIN_SHARES_OUT = 1_000
# Citigroup pre-split (~2.9e10) is the largest real US share count in this window. The old
# 1e11 gate let 41 published companies through with a denominator 1000x too large, e.g.
# Pentair at 9.84e10 shares reporting 0.078% ownership instead of about 78%.
MAX_SHARES_OUT = 35_000_000_000
# Relative ceiling (2026-10-18). An absolute floor cannot catch a denominator tagged in THOUSANDS:
# Simon Property shows 8,000 shares outstanding and Abercrombie 87,846, both above the floor and
# both 1000x too small, giving 7,249% and 4,672%. The cross-check in shares_out.py only fires when
# both XBRL tags exist. Measured over 67,672 company-quarters: p99 = 118%, p99.5 = 147%, p99.9 =
# 395%. Securities lending can plausibly double-report a holding; it cannot produce 300%. Above
# this ceiling the denominator is wrong, so the figure is suppressed with a recorded cause rather
# than published. 135 company-quarters (0.199%) are affected.
MAX_OWNERSHIP_PCT = 300.0


def collapse_to_grain(mc: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """One row per (manager_cik, cusip): the latest filing's report of a security wins.

    A manager CIK can have more than one selected filing. An earlier version summed the share
    counts where they differed, on the theory that separate filings covered different sub-advisers.
    Verification on 2026-10-19 showed that theory is never true in this data: across all 20
    quarters every manager with multiple selected filings is an original plus amendment(s), never
    two independent originals. So a security appearing in two of one manager's filings always means
    the later filing RESTATED that holding, and summing shipped the old number plus the corrected
    one. Aristotle Capital 2014Q4 was published at 376m shares against a corrected book of 194m,
    because the filer labelled a full restatement "NEW HOLDINGS".

    Filer labels cannot be trusted, but filing order can. Securities present only in the earlier
    filing are kept, so a genuinely additive amendment still adds.

    Returns the collapsed frame and the number of rows superseded.
    """
    mc = mc.sort_values(["manager_cik", "cusip", "filed_date", "accession"])
    g = mc.groupby(["manager_cik", "cusip"])
    n_superseded = int((g["accession"].transform("nunique") > 1).sum())
    mc = mc.copy()
    mc["n_source_filings"] = g["accession"].transform("nunique")
    return mc.drop_duplicates(["manager_cik", "cusip"], keep="last").copy(), n_superseded


def select_filings(f: pd.DataFrame, period: str) -> tuple[pd.DataFrame, list[str]]:
    notes = []
    f = f[(f["period_of_report"] == period) & (f["report_type"].str.upper() != "13F NOTICE")].copy()
    f["is_amend"] = f["form_type"].str.endswith("/A")
    f["atype"] = f["amendment_type"].fillna("").str.upper()
    f = f.sort_values(["manager_cik", "filed_date", "accession"])
    keep = []
    for cik, g in f.groupby("manager_cik"):
        orig = g[~g["is_amend"]]
        amends = g[g["is_amend"]]
        base = orig.tail(1)                      # latest original for the period
        if len(orig) > 1:
            notes.append(f"manager {cik}: {len(orig)} originals for the period, kept latest {base['accession'].iloc[0]}")
        chosen = [base] if len(base) else []
        for _, a in amends.iterrows():
            if a["atype"].startswith("RESTATEMENT") or (a["atype"] == "" and len(base)):
                chosen = [pd.DataFrame([a])]     # replaces everything before it
                if a["atype"] == "":
                    notes.append(f"manager {cik}: amendment {a['accession']} has no amendment type; treated as RESTATEMENT")
            elif a["atype"] == "":
                # blank type AND no original (the original was a 13F NOTICE, filtered above).
                # Appending every such amendment double-counted 9,886 holdings across 10 quarters
                # (decision 12, 2026-10-18). Amendments are sorted by filed date, so this keeps the
                # latest and nothing is counted twice.
                chosen = [pd.DataFrame([a])]
                notes.append(f"manager {cik}: amendment {a['accession']} has no amendment type and no "
                             f"original for the period; kept as the only filing")
            else:                                # explicit NEW HOLDINGS: genuinely additive
                chosen.append(pd.DataFrame([a]))
        keep.extend(chosen)
    sel = pd.concat(keep, ignore_index=True) if keep else f.iloc[0:0]
    return sel, notes


def shares_outstanding_table(label: str) -> tuple[pd.DataFrame, str]:
    so = pd.read_parquet(f"cache/parsed/{label}_shares_out.parquet")
    so["evidence"] = ""
    note = "XBRL only"
    rx = Path(f"cache/parsed/{label}_shares_out_regex.parquet")
    if rx.exists():
        r = pd.read_parquet(rx)
        r = r[~r["cik"].isin(so["cik"])]
        so = pd.concat([so, r[so.columns.intersection(r.columns)]], ignore_index=True)
        note = f"XBRL + regex fallback ({len(r):,} companies)"
    return so, note


def run(label: str, qend: str, period: str):
    h = pd.read_parquet(f"cache/parsed/{label}_holdings.parquet")
    f = pd.read_parquet(f"cache/parsed/{label}_filings.parquet")
    m = pd.read_csv(f"data/{label}_cusip_cik_map.csv", dtype={"cusip6": str, "cusip9": str})
    so, so_note = shares_outstanding_table(label)
    qe = pd.Timestamp(qend); ly, lq = qe.year, (qe.month - 1) // 3 + 1
    seclist = pd.read_parquet(f"cache/parsed/seclist_{ly}q{lq}.parquet")
    fund = fundsmod.load().set_index("cik")["reason"]
    f3 = fundsmod.f3_cusips(seclist)
    ntok = fundsmod.name_token_cusip6(seclist)
    out = [f"{label} ownership, quarter end {qend}, period_of_report {period}; shares outstanding: {so_note}"]
    sel, notes = select_filings(f, period)
    out.append(f"filings for the period: {len(f[f['period_of_report'] == period]):,}; after amendment/duplicate resolution: {len(sel):,} "
               f"({sel['form_type'].value_counts().to_dict()}); notes: {len(notes)} (first 5 below)")
    out.extend("  " + n for n in notes[:5])
    rows = h[h["accession"].isin(sel["accession"])]
    rows = rows[(rows["sh_prn"] != "PRN") & (rows["put_call"] == "") & rows["cusip_status"].isin(["ok", "repaired_check_digit", "repaired_pad_zeros"])]
    rows = rows[rows["shares"].fillna(0) > 0]
    out.append(f"holdings rows used: {len(rows):,} (SH, no put/call, resolved CUSIP, shares > 0)")
    # value per CUSIP (scale-normalized, for reporting only)
    sc = pd.read_parquet(f"cache/parsed/{label}_shares_check.parquet", columns=["accession", "cusip", "value_norm"])
    sc = sc[sc["accession"].isin(sel["accession"]) & (sc["value_norm"] <= 2e8)]
    v9 = sc.groupby("cusip")["value_norm"].sum(); v6 = sc.groupby(sc["cusip"].str[:6])["value_norm"].sum()
    # per manager x CUSIP
    mc = rows.groupby(["accession", "cusip"], as_index=False).agg(shares_held=("shares", "sum"), n_rows=("shares", "size"))
    _selcols = ["accession", "manager_cik", "manager_name", "filed_date"] + (["value_scale_flag"] if "value_scale_flag" in sel else [])
    mc = mc.merge(sel[_selcols], on="accession", validate="m:1")
    mc["cusip6"] = mc["cusip"].str[:6]
    m6 = m.drop_duplicates("cusip6").set_index("cusip6")      # map is sorted: most 13G/13D links first within an issuer
    mc["company_cik"] = mc["cusip6"].map(m6["company_cik"]); mc["company_name"] = mc["cusip6"].map(m6["company_name"])
    mc["map_conflict"] = mc["cusip6"].map(m6["conflict_flag"]); mc["map_conflict_two_sided"] = mc["cusip6"].map(m6["conflict_two_sided"])
    mc["map_source"] = mc["cusip6"].map(m6["map_source"])
    # ---- decision 2: fund exclusion
    reason = mc["company_cik"].map(fund)
    reason = reason.where(reason.notna(), mc["cusip"].map(f3))
    excl = mc[reason.notna()].assign(reason=reason[reason.notna()])
    mc = mc[reason.isna()].copy()
    excl_c9 = excl.drop_duplicates("cusip")
    excl_val = v9.reindex(excl_c9["cusip"]).fillna(0)
    excl_tab = excl_c9.assign(value=excl_val.values).groupby(excl_c9["reason"].str.slice(0, 2))["value"].agg(cusips="size", value_bn=lambda s: s.sum() / 1e6)
    out.append(f"\nFUNDS EXCLUDED (decision 2): {excl_c9['cusip'].nunique():,} CUSIPs on {excl_c9['company_cik'].nunique():,} CIKs, {len(excl):,} manager-CUSIP rows, "
               f"${excl_val.sum() / 1e6:,.1f}bn of 13F value = {excl_val.sum() / v9.sum():.1%} of the selected filings' value\n" + excl_tab.round(1).to_string())
    excl_c9.assign(value_k=excl_val.values).sort_values("value_k", ascending=False)[["cusip", "company_cik", "company_name", "reason", "value_k"]].to_csv(f"output/{label}_excluded_funds.csv", index=False)
    out.append("largest excluded:\n" + excl_c9.assign(value_bn=(excl_val.values / 1e6).round(1)).sort_values("value_bn", ascending=False).head(12)[["cusip", "company_cik", "company_name", "reason", "value_bn"]].to_string(index=False, max_colwidth=40))
    # double-count control: same manager cik + cusip in more than one selected filing (NEW HOLDINGS appends are legit; others flagged)
    dup = mc.groupby(["manager_cik", "cusip"])["accession"].nunique()
    mc["multi_filing_flag"] = mc.set_index(["manager_cik", "cusip"]).index.map(dup).values > 1
    # FLAGS ONLY (2026-10-11 stop-condition analysis; see ownership_whatif.txt): nothing is excluded by these.
    mc["debt_cusip_flag"] = mc["cusip"].str[6].str.isalpha()           # CUSIP issue number starting with a letter = fixed income
    # decision 12 (2026-10-18): issue number 9 marks a derivative or non-standard line. These passed
    # every filter when the filer left put_call blank and the check digit happened to validate:
    # 1,453 rows / 636,173,041 shares in 2010Q3, and 74% of the multi-CUSIP companies owed their
    # extra CUSIP to one. A derivative line is not a share holding.
    mc["derivative_cusip_flag"] = mc["cusip"].str[6] == "9"
    sl9 = seclist.drop_duplicates("cusip").set_index("cusip")["issuer_desc"]
    mc["list_desc"] = mc["cusip"].map(sl9).fillna("")
    mc["adr_flag"] = mc["list_desc"].str.contains(r"\bADR|\bADS|SPON ADR|SP ADR", regex=True)
    # Decision 15b (2026-10-21): three more security types that are not the common stock they were
    # being divided by. Same treatment as ADR and debt: the row stays in the output, flagged, and
    # leaves the ownership figure. All three are read from the SEC's own 13(f) list description, so
    # nothing is inferred from a CUSIP's shape.
    #   warrants and rights  "*W EXP 12/19/201", "RIGHT 99/99/9999". A warrant is not a share.
    #   dated units          "UNIT 99/99/9999" is a SPAC unit, one share bundled with a warrant.
    #                        Undated units are NOT caught: "COM UNIT LP", "UNIT LTD PARTN" and
    #                        "SH BEN INT" are the actual equity of a partnership or trust.
    #   preferred            "6.50% PFD CUM CO", "CV PFD-E 7.25%". A different security with its
    #                        own share count, and never part of common shares outstanding.
    # Chart Acquisition Corp 2014Q1 is the case: 571,003 common shares held of 3,566,447
    # outstanding is 16%, but 250,000 units and 403,498 warrants were added to the numerator and
    # published it at 296.8%, the highest figure left in the build after decision 15.
    _ud = mc["list_desc"].str.upper()
    mc["warrant_flag"] = _ud.str.contains(r"(?:^\*?W\b)|\bW EXP\b|\bWTS?\b|WARRANT|\bRTS?\b|\bRIGHT", regex=True)
    mc["unit_bundle_flag"] = _ud.str.contains(r"\b(?:UNIT|UT)\b.*\d{1,2}/\d{1,2}/\d{2,4}", regex=True)
    mc["preferred_flag"] = _ud.str.contains(r"\bPFD\b|PREFERRED|\bPRF\b|\bPREF\b", regex=True)
    dup_amend = set()
    selx = sel.set_index("accession")
    multi_mgr = mc.groupby("manager_cik")["accession"].nunique()
    for mcik, g in mc[mc["manager_cik"].isin(multi_mgr[multi_mgr > 1].index)].groupby("manager_cik"):
        accs = g["accession"].unique()
        if len(accs) < 2:
            continue
        orig = g[~selx.loc[g["accession"], "form_type"].str.endswith("/A").values]
        if not len(orig):
            continue
        o = orig.groupby("cusip")["shares_held"].sum()
        for acc in accs:
            if acc in orig["accession"].values:
                continue
            a = g[g["accession"] == acc].groupby("cusip")["shares_held"].sum()
            if (a.reindex(o.index) == o).sum() >= 0.9 * len(o):
                dup_amend.add(acc)
    mc["dup_amendment_flag"] = mc["accession"].isin(dup_amend)
    # (ii) duplicate NEW HOLDINGS amendments act as RESTATEMENTS: drop the manager's original rows
    dup_mgrs = set(mc.loc[mc["dup_amendment_flag"], "manager_cik"])
    orig_acc = set(selx.index[~selx["form_type"].str.endswith("/A")])
    drop_orig = mc["manager_cik"].isin(dup_mgrs) & mc["accession"].isin(orig_acc)
    n_orig_filings = mc.loc[drop_orig, "accession"].nunique(); n_orig_rows = int(drop_orig.sum())
    mc = mc[~drop_orig].copy()
    dup = mc.groupby(["manager_cik", "cusip"])["accession"].nunique()
    mc["multi_filing_flag"] = mc.set_index(["manager_cik", "cusip"]).index.map(dup).values > 1
    mc, n_superseded = collapse_to_grain(mc)
    out.append(f"\nGRAIN: one row per manager x security. Where a manager filed the same security "
               f"more than once the latest filing wins, never summed: {n_superseded:,} rows "
               f"superseded; final rows {len(mc):,}")
    # (i) + (iii) exclusions from the ownership figure; rows are kept in the output
    mc["excluded_from_ownership"] = np.where(mc["debt_cusip_flag"], "debt_cusip",
                                    np.where(mc["derivative_cusip_flag"], "derivative_cusip",
                                    np.where(mc["adr_flag"], "adr",
                                    np.where(mc["warrant_flag"], "warrant_or_right",
                                    np.where(mc["unit_bundle_flag"], "dated_unit",
                                    np.where(mc["preferred_flag"], "preferred", ""))))))
    own = mc[mc["excluded_from_ownership"] == ""]
    dv = v9.reindex(mc.loc[mc["debt_cusip_flag"]].drop_duplicates("cusip")["cusip"]).fillna(0).sum()
    av = v9.reindex(mc.loc[mc["adr_flag"]].drop_duplicates("cusip")["cusip"]).fillna(0).sum()
    out.append(f"\nFIXES (Luke 2026-10-12): debt-pattern CUSIPs excluded from ownership (rows kept): {int(mc['debt_cusip_flag'].sum()):,} rows / "
               f"{mc.loc[mc['debt_cusip_flag'], 'cusip'].nunique():,} CUSIPs / ${dv / 1e6:,.1f}bn; "
               f"ADR/ADS excluded from the main figure: {int(mc['adr_flag'].sum()):,} rows / {mc.loc[mc['adr_flag'], 'cusip'].nunique():,} CUSIPs on "
               f"{mc.loc[mc['adr_flag'], 'company_cik'].nunique():,} companies / ${av / 1e6:,.1f}bn; "
               f"warrants/rights excluded: {int(mc['warrant_flag'].sum()):,} rows / {mc.loc[mc['warrant_flag'], 'cusip'].nunique():,} CUSIPs; "
               f"dated (SPAC) units excluded: {int(mc['unit_bundle_flag'].sum()):,} rows / {mc.loc[mc['unit_bundle_flag'], 'cusip'].nunique():,} CUSIPs; "
               f"preferred excluded: {int(mc['preferred_flag'].sum()):,} rows / {mc.loc[mc['preferred_flag'], 'cusip'].nunique():,} CUSIPs; "
               f"NEW HOLDINGS amendments duplicating >= 90% of the original treated as restatements: {len(dup_amend):,} amendments, "
               f"{n_orig_filings:,} original filings / {n_orig_rows:,} rows dropped")
    # shares outstanding per company: undimensioned fact only (classes are never summed)
    und = so[so["class_axis"] == ""].drop_duplicates("cik").set_index("cik")
    cls = so[so["class_axis"] != ""].copy()
    # Decision 12's plausibility range applies to CLASS counts too. It was written against the
    # undimensioned count only, which was enough while class counts were used for a side figure;
    # decision 15 made them real denominators, and the first build after it shipped 146 rows in
    # 2014Q4 with a class count outside [MIN_SHARES_OUT, MAX_SHARES_OUT] and one holding larger
    # than its own denominator. The gate caught it before the data went anywhere.
    cls = cls[(cls["shares"] >= MIN_SHARES_OUT) & (cls["shares"] <= MAX_SHARES_OUT)]
    cls["letter"] = cls["class_axis"].str.extract(r"Class\s*([A-C])\b|Class([A-C])Member|([A-C])Member", expand=True).bfill(axis=1).iloc[:, 0]
    cls_n = cls.groupby("cik")["class_axis"].nunique()
    cls1 = cls[cls["letter"].notna()].drop_duplicates(["cik", "letter"]).set_index(["cik", "letter"])
    so_shares = und["shares"]
    so_src = und["shares_outstanding_source"]; so_date = und["shares_outstanding_date"]; so_gap = und["gap_flag"]; so_ev = und["evidence"]
    # ---- decision 12 plausibility gates (2026-10-18). Published values of 25,208,955,300% came from
    # XBRL scale/unit errors in the denominator (CSX = 1 share) and dollars-reported-as-shares in the
    # numerator (one manager filed 111,580,102,484 Microsoft shares against 8.4bn outstanding).
    # Neither is a market fact; both are measurement failures and are excluded, not published.
    so_plaus = so_shares.where((so_shares >= MIN_SHARES_OUT) & (so_shares <= MAX_SHARES_OUT))
    n_so_bad = int(so_shares.notna().sum() - so_plaus.notna().sum())
    mc["so_implausible_flag"] = mc["company_cik"].map(so_shares).notna() & mc["company_cik"].map(so_plaus).isna()
    # a single manager cannot hold more of a company than exists
    held_vs_out = mc["shares_held"] / mc["company_cik"].map(so_plaus)
    mc["impossible_holding_flag"] = held_vs_out > 1.0
    mc["excluded_from_ownership"] = np.where(mc["excluded_from_ownership"] != "", mc["excluded_from_ownership"],
                                   np.where(mc["so_implausible_flag"], "shares_outstanding_implausible",
                                   np.where(mc["impossible_holding_flag"], "holding_exceeds_shares_outstanding", "")))
    so_shares = so_plaus
    own = mc[mc["excluded_from_ownership"] == ""]
    out.append(f"\nPLAUSIBILITY GATES (decision 12): shares outstanding outside "
               f"[{MIN_SHARES_OUT:,.0f}, {MAX_SHARES_OUT:,.0f}] nulled: {n_so_bad:,} companies / "
               f"{int(mc['so_implausible_flag'].sum()):,} rows; single holdings exceeding shares "
               f"outstanding excluded: {int(mc['impossible_holding_flag'].sum()):,} rows / "
               f"{mc.loc[mc['impossible_holding_flag'], 'company_cik'].nunique():,} companies")
    # ---- which 13(f) class each held CUSIP is, from the SEC's own list description (decision 15).
    # Computed before the company roll-up because the roll-up now depends on it.
    desc = mc["list_desc"].fillna("").str.upper()
    mc["class_letter"] = desc.str.extract(r"\bCL(?:ASS)?\s*([A-C])\b", expand=False)
    mc.loc[desc.str.contains(r"\bSPL\b|SPECIAL|\bSER\b|SERIES", regex=True), "class_letter"] = np.nan   # special / series classes never match a plain class member
    mc["class_key"] = mc["class_letter"].fillna("COM")
    held_keys = own.index.to_series().map(mc["class_key"]).groupby(own["company_cik"]).apply(
        lambda s: frozenset(s.dropna()))
    # the class facts, deduplicated: one per letter, plus the largest unlettered one. Summing the raw
    # class_axis rows triple counts - Central Garden & Pet's common stock appears undimensioned, as
    # CommonStock and as CommonClassOne, all about 12.2m - and an inflated sum would make every
    # undimensioned count look too small to be a total.
    cls_let = cls[cls["letter"].notna()].drop_duplicates(["cik", "letter"]).groupby("cik")["shares"].sum()
    cls_unlet = cls[cls["letter"].isna()].groupby("cik")["shares"].max()
    cls_facts_sum = cls_let.add(cls_unlet, fill_value=0.0)

    # company level
    comp = own.groupby("company_cik", dropna=False).agg(shares_held_total=("shares_held", "sum"), n_managers=("manager_cik", "nunique"), n_cusips=("cusip", "nunique"), company_name=("company_name", "first")).reset_index()
    cls_by_cik = {cik: g.set_index("letter")["shares"].to_dict()
                  for cik, g in cls1.reset_index().groupby("cik")}

    def _denom(cik):
        und_v = so_shares.get(cik)
        return company_denominator(None if pd.isna(und_v) else und_v,
                                   held_keys.get(cik, frozenset()),
                                   cls_by_cik.get(cik, {}),
                                   cls_facts_sum.get(cik, 0.0))

    _d = comp["company_cik"].map(_denom)
    comp["shares_outstanding"] = [d[0] for d in _d]
    comp["denominator_basis"] = [d[1] for d in _d]
    _cause = pd.Series([d[2] for d in _d], index=comp.index)
    comp["multi_class_flag"] = comp["shares_outstanding"].isna() & comp["company_cik"].isin(cls_n.index)
    comp["institutional_ownership_pct"] = np.where(
        comp["shares_outstanding"].isna(), np.nan,
        comp["shares_held_total"] / comp["shares_outstanding"] * 100)
    # relative ceiling: suppress, do not publish, a figure whose denominator must be wrong
    _imp = comp["institutional_ownership_pct"] > MAX_OWNERSHIP_PCT
    comp["pct_suppressed_cause"] = np.where(~_imp, "",
                                   np.where(comp["n_cusips"] > 1, "multi_cusip_classes_summed",
                                            "shares_outstanding_scale_suspect"))
    # a class-coverage cause is the more specific statement of why there is no figure, so it wins
    comp["pct_suppressed_cause"] = np.where(_cause.ne("") & _cause.ne("no_shares_outstanding"),
                                            _cause, comp["pct_suppressed_cause"])
    comp.loc[_imp, "institutional_ownership_pct"] = np.nan
    _basis_n = comp["denominator_basis"].value_counts().to_dict()
    out.append(f"\nCLASS COVERAGE (decision 15): the denominator must cover the classes the "
               f"numerator sums. Companies by basis: {_basis_n}; combined-class denominators "
               f"{int((comp['denominator_basis'] == 'classes_combined').sum()):,}; withheld for "
               f"incomplete class counts {int((comp['denominator_basis'] == 'incomplete').sum()):,}; "
               f"withheld as ambiguous {int((comp['denominator_basis'] == 'ambiguous').sum()):,}")
    out.append(f"\nOWNERSHIP CEILING (decision 12): figures above {MAX_OWNERSHIP_PCT:.0f}% suppressed "
               f"as denominator errors: {int(_imp.sum()):,} companies "
               f"({int((comp['pct_suppressed_cause'] == 'multi_cusip_classes_summed').sum()):,} multi-CUSIP, "
               f"{int((comp['pct_suppressed_cause'] == 'shares_outstanding_scale_suspect').sum()):,} scale-suspect)")
    comp["so_gap_flag"] = comp["company_cik"].map(so_gap)
    # per-class figure per CUSIP (class_letter / class_key were set before the company roll-up)
    cu_held = own.groupby("cusip")["shares_held"].sum()
    mc["cusip_shares_held"] = mc["cusip"].map(cu_held)
    is_multi = mc["company_cik"].isin(comp.loc[comp["multi_class_flag"], "company_cik"])
    # a company whose figure rests on classes combined reports per CLASS at row level too: the
    # spec's shares_outstanding column is the count for that row's CUSIP, and for a dual-class
    # company the COM row and the CL A row do not share a denominator
    is_combined = mc["company_cik"].isin(
        comp.loc[comp["denominator_basis"].isin(["classes_combined", "single_class_matched"]),
                 "company_cik"])
    key = pd.MultiIndex.from_arrays([mc["company_cik"], mc["class_letter"]])
    cls_sh = pd.Series(key.map(cls1["shares"]), index=mc.index)
    cls_src = pd.Series(key.map(cls1["shares_outstanding_source"]), index=mc.index); cls_dt = pd.Series(key.map(cls1["shares_outstanding_date"]), index=mc.index)
    # the COM class of a combined company is the undimensioned count; its letter classes are the
    # class-dimensioned ones
    und_sh = mc["company_cik"].map(so_shares)
    row_class_sh = cls_sh.where(mc["class_letter"].notna(), und_sh)
    cls_src = cls_src.where(mc["class_letter"].notna(), mc["company_cik"].map(so_src))
    cls_dt = cls_dt.where(mc["class_letter"].notna(), mc["company_cik"].map(so_date))
    mc["class_shares_outstanding"] = np.where(is_multi | is_combined, row_class_sh, und_sh)
    mc["class_match"] = np.where(is_combined, "class-combined",
                        np.where(~is_multi & und_sh.notna(), "single-class",
                        np.where(is_multi & cls_sh.notna(), "matched",
                        np.where(is_multi, "unmatched", ""))))
    mc["class_ownership_pct"] = mc["cusip_shares_held"] / mc["class_shares_outstanding"] * 100
    mc.loc[mc["excluded_from_ownership"] != "", ["class_ownership_pct"]] = np.nan
    nm = comp["multi_class_flag"].sum(); mrows = mc[is_multi & (mc["excluded_from_ownership"] == "")]
    out.append(f"\nSHARE CLASSES (never summed): multi-class companies (class-dimensioned facts only) {nm:,}; their CUSIPs: matched to a class {mrows.loc[mrows['class_match'] == 'matched', 'cusip'].nunique():,} "
               f"(${v9.reindex(mrows.loc[mrows['class_match'] == 'matched', 'cusip'].unique()).fillna(0).sum() / 1e6:,.1f}bn), unmatched {mrows.loc[mrows['class_match'] == 'unmatched', 'cusip'].nunique():,} "
               f"(${v9.reindex(mrows.loc[mrows['class_match'] == 'unmatched', 'cusip'].unique()).fillna(0).sum() / 1e6:,.1f}bn); company-level pct is null for all {nm:,}")
    ex = mrows[mrows["class_match"] == "matched"].drop_duplicates("cusip").assign(value_bn=lambda d: v9.reindex(d["cusip"]).fillna(0).values / 1e6).sort_values("value_bn", ascending=False).head(8)
    out.append("largest per-class figures:\n" + ex[["company_name", "cusip", "list_desc", "cusip_shares_held", "class_shares_outstanding", "class_ownership_pct", "value_bn"]].round(1).to_string(index=False, max_colwidth=28))
    # row-level output
    mc["quarter_end"] = qend
    mc["shares_outstanding"] = mc["company_cik"].map(so_shares)
    _per_class = is_multi | is_combined
    mc["shares_outstanding_source"] = mc["company_cik"].map(so_src).where(~_per_class, cls_src); mc["shares_outstanding_date"] = mc["company_cik"].map(so_date).where(~_per_class, cls_dt)
    mc["shares_outstanding_evidence"] = mc["company_cik"].map(so_ev)
    mc["shares_outstanding"] = mc["shares_outstanding"].where(~_per_class, mc["class_shares_outstanding"])
    # Decision 12's "a single manager cannot hold more of a company than exists" was tested against
    # the company's undimensioned count. Since decision 15 the denominator PUBLISHED on a row can be
    # that row's class count, which is smaller, so the test has to run again against the number
    # actually published or it is not testing the published figure. Nine rows, one in each of nine
    # quarters, survived the first gate and failed the second; pipeline/validate.py caught them.
    _late = ((mc["excluded_from_ownership"] == "") & mc["shares_outstanding"].notna()
             & (mc["shares_held"] > mc["shares_outstanding"]))
    if _late.any():
        mc.loc[_late, "excluded_from_ownership"] = "holding_exceeds_shares_outstanding"
        mc.loc[_late, "class_ownership_pct"] = np.nan
        aff = mc.loc[_late, "company_cik"].unique()
        own = mc[mc["excluded_from_ownership"] == ""]
        ci = comp.set_index("company_cik")
        g = own[own["company_cik"].isin(aff)].groupby("company_cik")
        ci.loc[aff, "shares_held_total"] = g["shares_held"].sum().reindex(aff).fillna(0).values
        ci.loc[aff, "n_managers"] = g["manager_cik"].nunique().reindex(aff).fillna(0).values
        ci.loc[aff, "n_cusips"] = g["cusip"].nunique().reindex(aff).fillna(0).values
        pct = ci.loc[aff, "shares_held_total"] / ci.loc[aff, "shares_outstanding"] * 100
        ci.loc[aff, "institutional_ownership_pct"] = pct.where(ci.loc[aff, "shares_outstanding"].notna())
        over = ci.loc[aff, "institutional_ownership_pct"] > MAX_OWNERSHIP_PCT
        ci.loc[aff[over.fillna(False).to_numpy()], "pct_suppressed_cause"] = "shares_outstanding_scale_suspect"
        ci.loc[aff[over.fillna(False).to_numpy()], "institutional_ownership_pct"] = np.nan
        comp = ci.reset_index()
        out.append(f"\nIMPOSSIBLE HOLDINGS, second pass against the published denominator "
                   f"(decision 15): {int(_late.sum()):,} rows excluded on "
                   f"{len(aff):,} companies, whose figures were recomputed without them")
    mc["institutional_ownership_pct"] = mc["company_cik"].map(comp.set_index("company_cik")["institutional_ownership_pct"])
    # the company-level denominator, carried on every row so the company-grain file does not have to
    # guess which class count to use: a combined company's rows each carry their OWN class count in
    # shares_outstanding, and the two are different numbers on purpose (decision 15)
    mc["company_shares_outstanding"] = mc["company_cik"].map(comp.set_index("company_cik")["shares_outstanding"])
    mc["denominator_basis"] = mc["company_cik"].map(comp.set_index("company_cik")["denominator_basis"]).fillna("")
    mc.loc[mc["excluded_from_ownership"] != "", "institutional_ownership_pct"] = np.nan
    mc["multi_class_flag"] = mc["company_cik"].map(comp.set_index("company_cik")["multi_class_flag"]).fillna(False)
    mc["pct_suppressed_cause"] = mc["company_cik"].map(comp.set_index("company_cik")["pct_suppressed_cause"]).fillna("")
    mc = mc.rename(columns={"accession": "form_13f_accession_number"})
    mc["cusip_issuer"] = mc["cusip6"]
    mc["over_100_flag"] = False; mc["over_100_cause"] = ""
    comp.to_parquet(f"cache/parsed/{label}_ownership_company.parquet", index=False)
    # ---- report: coverage among operating companies
    all6 = pd.Index(v6.index)
    fund6 = set(excl["cusip6"]) | set(all6[all6.isin(ntok.index) & ~all6.isin(m6.index)])
    op6 = all6[~all6.isin(fund6)]
    mapped_op = op6[op6.isin(m6.index)]
    out.append(f"\nCUSIP->CIK coverage among OPERATING companies (6-char issuers, funds removed: {len(fund6):,} incl. {int((all6.isin(ntok.index) & ~all6.isin(m6.index)).sum()):,} unmapped by name token only): "
               f"{len(mapped_op):,} / {len(op6):,} = {len(mapped_op) / len(op6):.1%}; by value {v6[mapped_op].sum() / v6[op6].sum():.1%}; "
               f"by map source: {m6.loc[mapped_op, 'map_source'].value_counts().to_dict()}")
    c = comp[comp["company_cik"].notna()]
    has = c["shares_outstanding"].notna()
    vcik = v6.groupby(m6["company_cik"].reindex(v6.index)).sum()
    out.append(f"shares outstanding ({so_note}): companies with a figure {has.sum():,} / {len(c):,} = {has.mean():.1%}; by 13F value {vcik.reindex(c.loc[has, 'company_cik']).fillna(0).sum() / vcik.reindex(c['company_cik']).fillna(0).sum():.1%}; "
               f"gap > 100 days flagged: {c['so_gap_flag'].fillna(False).sum():,}; multi-class null: {c['multi_class_flag'].sum():,}")
    p = c["institutional_ownership_pct"].dropna()
    out.append(f"\nownership pct distribution (n={len(p):,}): " + p.describe(percentiles=[.05, .25, .5, .75, .95]).round(1).to_dict().__str__())
    bins = pd.cut(p, [-1, 0, 5, 25, 50, 75, 90, 100, 150, 1e9], labels=["0", "0-5", "5-25", "25-50", "50-75", "75-90", "90-100", "100-150", ">150"])
    out.append("histogram: " + bins.value_counts().sort_index().to_dict().__str__())
    over = c[c["institutional_ownership_pct"] > 100]
    out.append(f"companies over 100%: {len(over):,} / {len(p):,} = {len(over) / max(len(p), 1):.1%}")
    big = c[c["company_cik"].isin(vcik.sort_values(ascending=False).head(500).index)]
    bigp = big["institutional_ownership_pct"].dropna()
    out.append(f"large companies (top 500 by 13F value) with a pct: {len(bigp):,}; over 100%: {(bigp > 100).sum():,} = {(bigp > 100).mean():.1%}  [stop condition at 5%]")
    own = mc[mc["excluded_from_ownership"] == ""]       # re-derived: row-level columns were added above
    oc = []
    for _, r in over.iterrows():
        x = own[own["company_cik"] == r["company_cik"]]
        cause = []
        if r["institutional_ownership_pct"] > 500: cause.append("shares outstanding implausible (XBRL fact scale/units)")
        if x["multi_filing_flag"].any(): cause.append("manager-CUSIP in >1 filing")
        if r["so_gap_flag"]: cause.append("shares outstanding gap >100d")
        if (x["shares_held"] > 0.5 * r["shares_outstanding"]).any(): cause.append("single holding > 50% of shares out")
        if x["map_conflict"].fillna(0).max() == 1: cause.append("CUSIP->CIK conflict")
        if r["n_cusips"] > 1: cause.append("multiple CUSIPs summed (classes/units)")
        if not cause: cause.append("no identified data cause")
        sod = pd.to_datetime(x["shares_outstanding_date"].iloc[0], errors="coerce") if len(x) else pd.NaT
        if pd.notna(sod) and sod > qe: cause.append(f"[as-of {int((sod - qe).days)}d after quarter end: buybacks lower the denominator]")
        oc.append("; ".join(cause))
    over = over.assign(over_100_cause=oc)
    out.append("Note: companies with 'no identified data cause' can still exceed 100% through securities lending (the lender and the\n"
               "borrower's buyer both report the same shares on 13F); that is a possible explanation, not a measured cause.")
    out.append("over-100% causes (combinations; [..] = annotation):\n" + (pd.Series([c.split(" [")[0].rstrip("; ") for c in oc]).value_counts().head(14).to_string() if oc else "none") + f"\n  with the as-of date after quarter end: {sum('[as-of' in c for c in oc):,} of {len(oc):,}")
    ov = over.assign(value_bn=(vcik.reindex(over["company_cik"]).fillna(0).values / 1e6).round(2)).sort_values("value_bn", ascending=False)
    out.append("largest over-100% companies:\n" + ov.head(20)[["company_cik", "company_name", "n_managers", "shares_held_total", "shares_outstanding", "institutional_ownership_pct", "value_bn", "over_100_cause"]].round(1).to_string(index=False, max_colwidth=60))
    over.to_csv(f"output/problems/{label}/over_100_companies.csv", index=False)
    mc["over_100_flag"] = mc["company_cik"].isin(over["company_cik"])
    mc["over_100_cause"] = mc["company_cik"].map(over.set_index("company_cik")["over_100_cause"]).fillna("")
    write_output(mc, label)
    # missing shares outstanding, with causes from the EDGAR full index
    nso = c[~has].copy()
    idx = pd.read_parquet("cache/parsed/edgar_full_index_2010Q1_2015Q1.parquet")
    idx["date_filed"] = pd.to_datetime(idx["date_filed"])
    near = idx[(idx["date_filed"] >= qe - pd.Timedelta(days=200)) & (idx["date_filed"] <= qe + pd.Timedelta(days=200))]
    k10 = set(near.loc[near["form_type"].isin(["10-K", "10-Q", "10-KT", "10-QT", "10-K/A", "10-Q/A"]), "cik"])
    frn = set(near.loc[near["form_type"].isin(["20-F", "40-F", "20-F/A", "40-F/A", "6-K"]), "cik"])
    anyf = set(near["cik"])
    att = Path(f"cache/parsed/{label}_shares_out_regex_attempts.parquet")
    rx_status = pd.read_parquet(att).set_index("cik")["status"] if att.exists() else pd.Series(dtype=str)
    def cause_nso(cik):
        if cik in cls_n.index:
            return "class-dimensioned facts only: company pct null by rule, per-class pct given (class_ownership_pct)"
        if cik in rx_status.index and rx_status[cik] != "ok":
            return f"regex fallback tried: {rx_status[cik]}"
        if cik in k10:
            return "files 10-K/10-Q but no XBRL cover fact (XBRL phase-in / small filer)"
        if cik in frn:
            return "foreign private issuer (20-F/40-F/6-K): no dei cover fact"
        if cik in anyf:
            return "other EDGAR filings only near quarter end (no 10-K/10-Q/20-F/40-F)"
        return "no EDGAR filing within 200 days of quarter end"
    nso["cause"] = nso["company_cik"].map(cause_nso)
    nso_val = vcik.reindex(nso["company_cik"]).fillna(0)
    nso["value_bn"] = (nso_val.values / 1e6).round(2)
    cz = nso.groupby("cause")["value_bn"].agg(companies="size", value_bn="sum").sort_values("value_bn", ascending=False)
    out.append(f"\nNO COMPANY-LEVEL FIGURE: {len(nso):,} companies carrying ${nso_val.sum() / 1e6:,.1f}bn = {nso_val.sum() / vcik.reindex(c['company_cik']).fillna(0).sum():.1%} of mapped operating value; causes:\n" + cz.round(1).to_string())
    out.append("largest without shares outstanding:\n" + nso.sort_values("value_bn", ascending=False).head(12)[["company_cik", "company_name", "n_managers", "value_bn", "cause"]].to_string(index=False, max_colwidth=40))
    txt = "\n".join(out); Path(f"output/problems/{label}").mkdir(parents=True, exist_ok=True)
    open(f"output/problems/{label}/ownership_report.txt", "w").write(txt); print(txt)
    return comp, mc


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3])
