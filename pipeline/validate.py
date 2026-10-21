"""Properties the output must satisfy. The build fails if any of them is violated.

Written 2026-10-19 after three rounds of review found defects only AFTER publication. Every check
here corresponds to something that actually shipped wrong at least once, named in the comment. The
point is that the code remembers the rule, not the person running it.

  python3 -m pipeline.validate <label> [<label> ...]   check per-quarter outputs
  python3 -m pipeline.validate --all                   check every quarter found in output/
  python3 -m pipeline.validate --deliverable           check the two final files
  python3 -m pipeline.validate --all --baseline        also write/refresh the regression baseline

Exit status is non-zero if any check FAILS, so it can gate a push or a release.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

MIN_SHARES_OUT = 1_000
MAX_SHARES_OUT = 35_000_000_000          # Citigroup pre-split (~2.9e10) is the largest real count
MAX_OWNERSHIP_PCT = 300.0
ACCESSION_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")
SPEC_12 = ["quarter_end", "company_name", "company_cik", "cusip", "manager_cik", "manager_name",
           "shares_held", "shares_outstanding", "institutional_ownership_pct",
           "form_13f_accession_number", "shares_outstanding_source", "shares_outstanding_date"]
BASELINE = "output/problems/validate_baseline.json"
CHUNK = 300_000


def cusip_check_digit_ok(c: str) -> bool:
    if not isinstance(c, str) or len(c) != 9:
        return False
    total = 0
    for i, ch in enumerate(c[:8]):
        v = int(ch) if ch.isdigit() else (ord(ch.upper()) - 55 if ch.isalpha() else {"*": 36, "@": 37, "#": 38}.get(ch, -1))
        if v < 0:
            return False
        if i % 2:
            v *= 2
        total += v // 10 + v % 10
    return (10 - total % 10) % 10 == int(c[8]) if c[8].isdigit() else False


class Result:
    def __init__(self):
        self.rows = []

    def add(self, scope, name, ok, detail=""):
        self.rows.append((scope, name, ok, detail))

    def failed(self):
        return [r for r in self.rows if not r[2]]

    def report(self):
        for scope, name, ok, detail in self.rows:
            if not ok:
                print(f"  FAIL  {scope}: {name}\n          {detail}")
        n_fail = len(self.failed())
        print(f"\n{len(self.rows)} checks, {n_fail} failed")
        return n_fail


def check_quarter(label: str, r: Result) -> dict:
    """Stream one per-quarter 31-column file. Returns metrics for the regression baseline."""
    path = f"output/{label}_institutional_ownership.csv"
    if not os.path.exists(path):
        r.add(label, "output file exists", False, path)
        return {}
    seen = set()
    m = dict(rows=0, dup_grain=0, bad_accession=0, bad_cusip=0, float_id=0, neg_shares=0,
             so_out_of_range=0, pct_over_ceiling=0, pct_negative=0, missing_source=0,
             holding_exceeds_so=0, pct_notnull=0, companies=set(), managers=set())
    for ch in pd.read_csv(path, dtype=str, chunksize=CHUNK, low_memory=False):
        if m["rows"] == 0:
            # the 12 spec columns must come first, in order (the deliverable is cut from these)
            r.add(label, "first 12 columns are the spec columns in order",
                  list(ch.columns[:12]) == SPEC_12, f"got {list(ch.columns[:12])}")
        m["rows"] += len(ch)
        key = ch["quarter_end"] + "|" + ch["cusip"].fillna("") + "|" + ch["manager_cik"].fillna("")
        m["dup_grain"] += int(key.isin(seen).sum()) + int(key.duplicated().sum())
        seen.update(key)
        acc = ch["form_13f_accession_number"].fillna("")
        m["bad_accession"] += int((~acc.map(lambda x: bool(ACCESSION_RE.match(x)))).sum())
        cus = ch["cusip"].fillna("")
        m["bad_cusip"] += int((~cus.map(cusip_check_digit_ok)).sum())
        for col in ("company_cik", "manager_cik", "shares_held", "shares_outstanding"):
            m["float_id"] += int(ch[col].fillna("").str.contains(r"\.", regex=True).sum())
        sh = pd.to_numeric(ch["shares_held"], errors="coerce")
        so = pd.to_numeric(ch["shares_outstanding"], errors="coerce")
        pct = pd.to_numeric(ch["institutional_ownership_pct"], errors="coerce")
        m["neg_shares"] += int((sh.fillna(1) <= 0).sum())
        m["so_out_of_range"] += int((so.notna() & ((so < MIN_SHARES_OUT) | (so > MAX_SHARES_OUT))).sum())
        m["pct_over_ceiling"] += int((pct > MAX_OWNERSHIP_PCT).sum())
        m["pct_negative"] += int((pct < 0).sum())
        m["pct_notnull"] += int(pct.notna().sum())
        m["missing_source"] += int((so.notna() & ch["shares_outstanding_source"].fillna("").eq("")).sum())
        pubs = pct.notna()
        m["holding_exceeds_so"] += int((pubs & so.notna() & (sh > so)).sum())
        m["companies"].update(ch.loc[ch["company_cik"].notna(), "company_cik"].unique())
        m["managers"].update(ch["manager_cik"].dropna().unique())

    # Each of these shipped wrong at least once. The comment names when.
    r.add(label, "grain unique (quarter, cusip, manager)", m["dup_grain"] == 0,
          f"{m['dup_grain']:,} duplicates (9,886 shipped before 2026-10-18)")
    r.add(label, "accession format", m["bad_accession"] == 0, f"{m['bad_accession']:,} malformed")
    r.add(label, "CUSIP check digit", m["bad_cusip"] == 0, f"{m['bad_cusip']:,} invalid")
    r.add(label, "identifiers are integers", m["float_id"] == 0,
          f"{m['float_id']:,} float-formatted (13.5M shipped as '732717.0')")
    r.add(label, "shares_held positive", m["neg_shares"] == 0, f"{m['neg_shares']:,} non-positive")
    r.add(label, f"shares_outstanding in [{MIN_SHARES_OUT:,}, {MAX_SHARES_OUT:,}]",
          m["so_out_of_range"] == 0,
          f"{m['so_out_of_range']:,} outside (CSX shipped 1 share; Pentair 9.84e10)")
    r.add(label, f"ownership <= {MAX_OWNERSHIP_PCT:.0f}%", m["pct_over_ceiling"] == 0,
          f"{m['pct_over_ceiling']:,} above (25,208,955,300% shipped before 2026-10-18)")
    r.add(label, "ownership non-negative", m["pct_negative"] == 0, f"{m['pct_negative']:,} negative")
    r.add(label, "denominator has a source", m["missing_source"] == 0,
          f"{m['missing_source']:,} rows with a denominator and no source")
    r.add(label, "no published holding exceeds shares outstanding", m["holding_exceeds_so"] == 0,
          f"{m['holding_exceeds_so']:,} rows (Microsoft 2011Q1 shipped 111bn shares)")
    return {"rows": m["rows"], "pct_notnull": m["pct_notnull"],
            "companies": len(m["companies"]), "managers": len(m["managers"])}


def check_company_file(r: Result):
    path = "output/company_ownership_by_quarter.csv"
    if not os.path.exists(path):
        r.add("company", "file exists", False, path)
        return
    c = pd.read_csv(path)
    r.add("company", "one row per (quarter, company)",
          not c.duplicated(["quarter_end", "company_cik"]).any(),
          f"{int(c.duplicated(['quarter_end','company_cik']).sum()):,} duplicates")
    pub = c[c["institutional_ownership_pct"].notna()]
    r.add("company", f"no published figure above {MAX_OWNERSHIP_PCT:.0f}%",
          (pub["institutional_ownership_pct"] <= MAX_OWNERSHIP_PCT).all(),
          f"max {pub['institutional_ownership_pct'].max():.1f}%")
    # the published percentage must equal its own two published columns
    recomp = pub["shares_held_total"] / pub["shares_outstanding"] * 100
    bad = (recomp - pub["institutional_ownership_pct"]).abs() > 0.01
    r.add("company", "percentage recomputes from its own columns", not bad.any(),
          f"{int(bad.sum()):,} rows disagree with shares_held_total / shares_outstanding")
    # a suppressed figure must say why
    sup = c[c["institutional_ownership_pct"].isna() & (c["shares_outstanding"].notna())]
    nocause = sup[sup["pct_suppressed_cause"].fillna("").eq("") & sup["multi_class_flag"].ne(True)]
    r.add("company", "a withheld figure records a reason", len(nocause) == 0,
          f"{len(nocause):,} rows have a denominator, no figure and no stated cause")


def check_manifest(r: Result):
    path = "output/deliverable_manifest.json"
    if not os.path.exists(path):
        r.add("manifest", "exists", False, path)
        return
    man = json.load(open(path))
    r.add("manifest", "covers 20 quarters", man.get("quarter_count") == 20,
          f"{man.get('quarter_count')} quarters")
    # the manifest must be newer than every file it describes, or it is describing a past state
    stale = []
    mtime = os.path.getmtime(path)
    for q in man.get("quarters", []):
        f = q.get("file")
        if f and os.path.exists(f) and os.path.getmtime(f) > mtime + 1:
            stale.append(os.path.basename(f))
    r.add("manifest", "written after the data it describes", not stale,
          f"{len(stale)} files newer than the manifest: {stale[:3]}")


def check_continuity(r: Result) -> dict:
    """Properties of the cross-quarter denominator check (pipeline/continuity.py).

    These are not checks on the published CSVs; they are checks on the rule that judges them, and
    each one names a mistake that was actually made while writing that rule. The two files are
    written by `python3 -m pipeline.continuity`; when they are absent the checks are skipped rather
    than failed, because the continuity report is a diagnostic, not part of the deliverable."""
    parq, met_path = "cache/parsed/shares_out_continuity.parquet", "output/problems/continuity_metrics.json"
    if not (os.path.exists(parq) and os.path.exists(met_path)):
        print("continuity: not run, 0 checks (python3 -m pipeline.continuity)")
        return {}
    c = pd.read_parquet(parq)
    met = json.load(open(met_path))
    rep = c[c["shares_repaired"].notna()]
    r.add("continuity", "covers 20 quarters", met.get("quarters") == 20, f"{met.get('quarters')}")
    r.add("continuity", f"every proposed denominator is in [{MIN_SHARES_OUT:,}, {MAX_SHARES_OUT:,}]",
          bool(((rep["shares_repaired"] >= MIN_SHARES_OUT)
                & (rep["shares_repaired"] <= MAX_SHARES_OUT)).all()),
          f"{int(((rep['shares_repaired'] < MIN_SHARES_OUT) | (rep['shares_repaired'] > MAX_SHARES_OUT)).sum()):,} outside")
    # a split is not an error: the ownership figure must never be "fixed" by undoing a corporate action
    r.add("continuity", "no repair proposed on a level shift the series kept",
          not (c["continuity_label"].eq("level_shift") & c["shares_repaired"].notna()).any(),
          "a corporate action was treated as a units error")
    # the defect this check exists for: the correction threshold was compared against the raw
    # factor, so 0.001 (a value tagged in thousands, Apple 2014Q1) failed it and only the
    # too-large direction was ever repaired
    corr = pd.concat([rep["scale_factor"], 1 / rep["scale_factor"]], axis=1).max(axis=1)
    r.add("continuity", "every correction is at least 100x in whichever direction it goes",
          bool((corr >= 100).all()), f"{int((corr < 100).sum()):,} below 100x")
    r.add("continuity", "both directions of scale error are represented",
          bool((rep["scale_factor"] < 1).any() and (rep["scale_factor"] > 1).any()),
          "one direction is missing entirely, which is how the first version shipped")
    r.add("continuity", "every repair has at least 3 possible quarters of history behind it",
          bool((rep["level_confidence"] >= 3).all()),
          f"{int((rep['level_confidence'] < 3).sum()):,} repairs rest on fewer")
    r.add("continuity", "the panel is newer than the company file it is compared against",
          os.path.getmtime(parq) >= os.path.getmtime("output/company_ownership_by_quarter.csv") - 1,
          "the continuity report describes an older build; re-run pipeline.continuity")
    return {"continuity": {k: met[k] for k in sorted(met)}}


def check_regression(metrics: dict, r: Result, write: bool):
    """Compare this build with the last one. Every defect found in this project moved a number in
    the wrong direction, so a build-over-build comparison catches them without naming them."""
    prev = json.load(open(BASELINE)) if os.path.exists(BASELINE) else {}
    for label, m in sorted(metrics.items()):
        p = prev.get(label)
        if not p:
            r.add(label, "regression vs previous build", True, "no baseline yet")
            continue
        for field, tol in (("rows", 0.02), ("pct_notnull", 0.02), ("companies", 0.05)):
            was, now = p.get(field, 0), m.get(field, 0)
            drop = (was - now) / was if was else 0
            r.add(label, f"{field} did not fall more than {tol:.0%}", drop <= tol,
                  f"{was:,} -> {now:,} ({-drop:+.1%})")
    if write:
        Path(BASELINE).parent.mkdir(parents=True, exist_ok=True)
        json.dump(metrics, open(BASELINE, "w"), indent=2, sort_keys=True)
        print(f"baseline written -> {BASELINE}")


def main() -> int:
    args = sys.argv[1:]
    write_baseline = "--baseline" in args
    args = [a for a in args if a != "--baseline"]
    labels = []
    if "--all" in args or not args or args == ["--deliverable"]:
        labels = sorted(os.path.basename(p).replace("_institutional_ownership.csv", "")
                        for p in glob.glob("output/*_institutional_ownership.csv"))
    else:
        labels = [a for a in args if not a.startswith("--")]

    r = Result()
    metrics = {}
    print(f"validate: {len(labels)} quarter(s)")
    for label in labels:
        m = check_quarter(label, r)
        if m:
            metrics[label] = m
    check_company_file(r)
    check_manifest(r)
    check_continuity(r)
    check_regression(metrics, r, write_baseline)
    n = r.report()
    print("PASS" if n == 0 else "FAIL")
    return 1 if n else 0


if __name__ == "__main__":
    sys.path.insert(0, ".")
    sys.exit(main())
