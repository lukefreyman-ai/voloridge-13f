"""Cross-quarter continuity of the shares-outstanding denominator.

Why this exists. Every denominator defect this project shipped was found by looking at ONE quarter,
where a units error and a corporate action are indistinguishable: Apple 2014Q1 carried 861,745
shares against a real 861,381,000 (tagged in thousands), Oracle 2012Q2 carried 4.819e15, Pentair
carried 9.84e10 against a real ~1e8, CSX carried 1 share. A per-quarter rule has to guess. A
company's own 20-quarter history does not have to guess: a 1,000x or 1,000,000x step that the
series contradicts is a tagging error, a 5x step that the series KEEPS is a reverse split.

So the unit of judgment here is the series (cik x share class across 2010Q1-2014Q4), not the row.

The taxonomy, one label per observation. Each rule names the real case it was written for:
  implausible_scale   the value is outside any possible US share count and a power of ten puts it
                      back on the company's own level. Stryker 2010-2011 carries ~380 shares
                      (tagged in millions) against a real ~3.9e8; PG&E 2014Q4 carries 4.759e14.
  isolated_scale      the value is possible on its own, but both neighbours disagree with it in the
                      same direction by more than 5x and a power of ten reconciles it. Apple 2014Q1.
  level_shift         the level changes at this quarter and the series KEEPS the new level, and the
                      new level is possible: a split, a reverse split, a buyback, an issuance.
                      Chimera Investment's 1-for-5 reverse split and Apple's 7-for-1 split land
                      here and are deliberately NOT repaired.
  unexplained         a break no power of ten explains and the series does not keep. Reported, never
                      repaired: these are the rows a human should look at.
  ok                  within 5x of the company's own local level.

A repair is proposed ONLY for the two scale labels, only when the factor is >= 100x (a thousands or
millions tagging error, never a 10x corporate action), and only when the result is plausible AND
lands within 1.5x of the level the rest of the series agrees on. Nothing here is merged into the
published denominator: `python3 -m pipeline.continuity` writes the report and
cache/parsed/shares_out_continuity.parquet, and pipeline/ownership.py does not read it until Luke
approves the merge (decision 14 in STATUS.md).

  python3 -m pipeline.continuity              # all 20 quarters -> report + parquet
  python3 -m pipeline.continuity --quiet      # write the files, print only the summary line
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import ownership
from .quarters import ALL_LABELS, spec

# A real US share count in 2010-2014. Citigroup pre-split (~2.9e10) is the largest; the floor is
# the one pipeline/ownership.py already publishes against, kept identical on purpose.
MIN_SHARES_OUT = ownership.MIN_SHARES_OUT
MAX_SHARES_OUT = ownership.MAX_SHARES_OUT
# 5x is the break threshold. Real quarter-over-quarter moves are far smaller: the largest genuine
# move in this panel that is not a split is under 3x. A 1-for-5 reverse split sits exactly at 5x,
# which is why a break alone is never enough to repair anything - the label decides that.
BREAK_RATIO = 5.0
# A repair must land this close to the level the rest of the series agrees on, or it is not a repair.
REPAIR_TOL = 1.5
# Only thousands/millions/billions tagging is repaired. 10x is excluded deliberately: a 1-for-10
# reverse split is a power of ten AND a real corporate action, so 10x can never be told apart from
# a tagging error by magnitude alone.
MIN_REPAIR_FACTOR = 100.0
NEIGHBOURS = 4            # how many quarters either side form the local level
# A repair needs this many possible quarters of the company's own history behind the level. Two
# quarters can both be wrong the same way; the 2010 phase-in quarters are where that happens.
MIN_REPAIR_CONFIDENCE = 3
# Above this, a break is worth a human's time; below it, the history is too thin to argue with.
ACTIONABLE_CONFIDENCE = 3

REPORT_TXT = "output/problems/continuity_shares_out.txt"
REPORT_CSV = "output/problems/continuity_shares_out.csv"
BAND_CSV = "output/problems/continuity_published_over_100.csv"
METRICS = "output/problems/continuity_metrics.json"
PARQUET = "cache/parsed/shares_out_continuity.parquet"
SCALE_LABELS = ("implausible_scale", "isolated_scale")


def panel(labels: list[str] | None = None) -> pd.DataFrame:
    """One row per (cik, class, quarter): the denominator pool ownership.py actually publishes from,
    which is the XBRL table plus the approved 10-K regex fallback, not the XBRL parquet alone."""
    parts = []
    for lab in labels or ALL_LABELS:
        so, _ = ownership.shares_outstanding_table(lab)
        so = so.copy()
        so["label"] = lab
        so["quarter_end"] = pd.Timestamp(spec(lab)["quarter_end"])
        keep = ["cik", "name", "class_axis", "shares", "label", "quarter_end",
                "shares_outstanding_source", "shares_outstanding_date", "tag", "scale_corrected"]
        parts.append(so.reindex(columns=keep))
    p = pd.concat(parts, ignore_index=True)
    p["class_axis"] = p["class_axis"].fillna("")
    p["shares"] = pd.to_numeric(p["shares"], errors="coerce")
    p = p[p["shares"].notna() & (p["shares"] > 0)]
    return p.sort_values(["cik", "class_axis", "quarter_end"]).reset_index(drop=True)


def _neighbour_levels(x: np.ndarray, usable: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Median of up to NEIGHBOURS points before, and after, each point of one series (log space).

    Two rules, both learned from this panel:
      - the point itself is excluded: a value cannot vouch for itself.
      - only POSSIBLE values form the level. The first version of this function used every
        neighbour, and the result was backwards on exactly the companies it was written for: The
        Phoenix Companies carries ~116 shares in most quarters (tagged in millions), so the level
        came out at 116 and the one CORRECT quarter, 116,300,000, was flagged as the break. A
        value outside [MIN_SHARES_OUT, MAX_SHARES_OUT] cannot be anyone's evidence.
    Returns (level before, level after, how many possible quarters formed the two levels).
    NaN where that side has no usable point."""
    n = len(x)
    before = np.full(n, np.nan)
    after = np.full(n, np.nan)
    n_used = np.zeros(n, dtype=int)
    ok = np.flatnonzero(usable)
    for i in range(n):
        lo = ok[ok < i][-NEIGHBOURS:]
        hi = ok[ok > i][:NEIGHBOURS]
        if len(lo):
            before[i] = np.median(x[lo])
        if len(hi):
            after[i] = np.median(x[hi])
        n_used[i] = len(lo) + len(hi)
    return before, after, n_used


def classify(p: pd.DataFrame) -> pd.DataFrame:
    """Add the continuity label, the proposed factor and the proposed repair. Pure function of the
    panel: no file reads, so tests can hand it three rows."""
    p = p.copy()
    lg = np.log10(p["shares"].to_numpy())
    possible = ((p["shares"] >= MIN_SHARES_OUT) & (p["shares"] <= MAX_SHARES_OUT)).to_numpy()
    before = np.full(len(p), np.nan)
    after = np.full(len(p), np.nan)
    n_used = np.zeros(len(p), dtype=int)
    # groupby over series; positions are contiguous because panel() sorted them
    for _, idx in p.groupby(["cik", "class_axis"], sort=False).indices.items():
        b, a, u = _neighbour_levels(lg[idx], possible[idx])
        before[idx], after[idx], n_used[idx] = b, a, u
    both = np.where(np.isnan(before), after, np.where(np.isnan(after), before, (before + after) / 2))
    p["n_quarters"] = p.groupby(["cik", "class_axis"])["shares"].transform("size")
    # How many possible quarters of this company's own history formed the level. A break against
    # one neighbour is an opinion; a break against six is evidence. The 2010 quarters are the
    # reason this column exists: XBRL coverage was still phasing in, so a 2010Q1 series often has
    # one usable neighbour, and nothing there should be acted on with the confidence of a 2013 case.
    p["level_confidence"] = n_used
    p["level_before"] = 10.0 ** before
    p["level_after"] = 10.0 ** after
    p["level"] = 10.0 ** both

    brk = np.log10(BREAK_RATIO)
    dev_b, dev_a = lg - before, lg - after
    off_before = np.abs(dev_b) > brk
    off_after = np.abs(dev_a) > brk
    # "the series keeps the new level": this point agrees with what comes after but not with what
    # came before. With no 'after' (the last quarter of a series) nothing is kept, so it cannot be
    # a level shift - that is what makes the last point of a series the hardest case, and it falls
    # through to unexplained rather than being waved through.
    kept = off_before & ~off_after & ~np.isnan(after)
    isolated = off_before & off_after & (np.sign(dev_b) == np.sign(dev_a))
    implausible = (p["shares"] < MIN_SHARES_OUT) | (p["shares"] > MAX_SHARES_OUT)

    # the power of ten that would put this value on its own series' level
    with np.errstate(invalid="ignore"):
        k = np.where(np.isnan(both), np.nan, np.round(lg - both))
    factor = 10.0 ** k
    repaired = p["shares"].to_numpy() / factor
    # The SIZE of the correction, which is 1,000x whether the value is a thousand times too large
    # or a thousand times too small. Comparing `factor` itself against the threshold was wrong in
    # exactly one direction: a value tagged in thousands has factor 0.001, so `abs(factor) >= 100`
    # rejected it and the Apple 2014Q1 case - the case this module was written for - came out
    # "unexplained" and unrepaired. tests/test_continuity.py pins both directions.
    correction = np.maximum(factor, 1.0 / factor)
    reconciles = (np.abs(np.log10(repaired) - both) <= np.log10(REPAIR_TOL)) \
        & (correction >= MIN_REPAIR_FACTOR) \
        & (repaired >= MIN_SHARES_OUT) & (repaired <= MAX_SHARES_OUT) \
        & (n_used >= MIN_REPAIR_CONFIDENCE)

    label = np.full(len(p), "ok", dtype=object)
    # order matters: an impossible value is wrong whatever the neighbours say, and a series that
    # keeps a possible new level is a corporate action even when the ratio is a power of ten.
    label = np.where(isolated, "isolated_scale", label)
    label = np.where(isolated & ~reconciles, "unexplained", label)
    label = np.where(kept & ~implausible, "level_shift", label)
    label = np.where(kept & implausible & reconciles, "implausible_scale", label)
    label = np.where(kept & implausible & ~reconciles, "unexplained", label)
    label = np.where(implausible & reconciles & ~kept, "implausible_scale", label)
    label = np.where(implausible & ~reconciles & ~kept, "unexplained", label)
    # A break at the EDGE of a series, where only one side exists. The first version called all of
    # these unexplained, which was its own one-directional rule: a value 1,000x off the only four
    # quarters it has is just as contradicted as one in the middle, and the 2010 quarters and every
    # company's last quarter are all edges. So a one-sided break is repairable on the same terms as
    # any other - a power of ten, a possible result, and MIN_REPAIR_CONFIDENCE quarters behind it -
    # and MIN_REPAIR_FACTOR still keeps a 1-for-10 reverse split in the final quarter out of it.
    only_one_side = (np.isnan(before) | np.isnan(after))
    one_sided_break = (label == "ok") & only_one_side & (off_before | off_after)
    label = np.where(one_sided_break & reconciles, "isolated_scale", label)
    label = np.where(one_sided_break & ~reconciles, "unexplained", label)
    # a single-quarter series has nothing to compare against; say so rather than calling it ok
    label = np.where(p["n_quarters"].to_numpy() == 1, "no_history", label)
    # no POSSIBLE neighbour anywhere in the series: there is no level, so there is nothing to be
    # continuous with. Reported separately from "unexplained" on purpose - "the history contradicts
    # this value" and "the company has no usable history" are different facts about the data, and
    # lumping them together was the first version's worst reporting error (2,785 of 5,170
    # "unexplained" rows were really this).
    label = np.where(np.isnan(both) & (p["n_quarters"].to_numpy() > 1), "no_usable_level", label)

    p["continuity_label"] = label
    p["scale_factor"] = np.where(np.isin(label, SCALE_LABELS), factor, np.nan)
    p["shares_repaired"] = np.where(np.isin(label, SCALE_LABELS), repaired, np.nan)
    p["deviation_x"] = np.where(np.isnan(both), np.nan, 10.0 ** (lg - both))
    # How the LEVEL itself moved across this quarter, independent of whether this observation is a
    # break: level_after / level_before. This is the column the over-100% diagnosis needs. Chimera
    # Investment 2014Q4 is the case: its denominator steps to 0.2x on a 1-for-5 reverse split while
    # the holdings reported against it are pre-split, so the figure was suppressed as
    # "multi_cusip_classes_summed" when the real cause was a corporate action. A cause assigned
    # from n_cusips cannot tell those apart; this can.
    p["shift_x"] = 10.0 ** (after - before)
    return p


def report(c: pd.DataFrame) -> str:
    flagged = c[~c["continuity_label"].isin(["ok", "no_history", "no_usable_level"])]
    out = [f"shares-outstanding continuity, {c['label'].nunique()} quarters, "
           f"{len(c):,} company-quarter-class observations on "
           f"{c.groupby(['cik', 'class_axis']).ngroups:,} series",
           f"break threshold {BREAK_RATIO:.0f}x against the median of up to {NEIGHBOURS} quarters "
           f"either side; repair only for factors >= {MIN_REPAIR_FACTOR:.0f}x landing within "
           f"{REPAIR_TOL}x of the series level", ""]
    counts = c["continuity_label"].value_counts()
    for name in ("ok", "no_history", "no_usable_level", "level_shift", "implausible_scale",
                 "isolated_scale", "unexplained"):
        n = int(counts.get(name, 0))
        out.append(f"  {name:<20} {n:>7,}  ({100 * n / max(len(c), 1):5.2f}%)")
    rep = c[c["shares_repaired"].notna()]
    out += ["", f"repairs proposed: {len(rep):,} observations on {rep['cik'].nunique():,} companies "
                f"({rep.groupby(['cik', 'class_axis']).ngroups:,} series)"]
    if len(rep):
        # a factor below 1 means the published value is that many times too SMALL (tagged in
        # thousands); above 1, too large. Printing the raw factor as an integer rounded every
        # too-small case to "0x", which hid half the population.
        size = rep["scale_factor"].map(lambda f: f"{f:,.0f}x too large" if f > 1
                                       else f"{1 / f:,.0f}x too small")
        out.append("  by correction: " + ", ".join(f"{k}: {v:,}" for k, v in
                                                   size.value_counts().sort_index().items()))
        out.append(f"  of those, denominators the current build must already be dropping as "
                   f"implausible: {int((rep['continuity_label'] == 'implausible_scale').sum()):,}")
    unx = flagged[(flagged["continuity_label"] == "unexplained")
                  & (flagged["level_confidence"] >= ACTIONABLE_CONFIDENCE)]
    thin = int(((c["continuity_label"] == "unexplained")
                & (c["level_confidence"] < ACTIONABLE_CONFIDENCE)).sum())
    out.append(f"unexplained breaks against fewer than {ACTIONABLE_CONFIDENCE} possible quarters of "
               f"history (too thin to act on, mostly the 2010 XBRL phase-in): {thin:,}")
    if len(unx):
        out += ["", f"unexplained breaks with at least {ACTIONABLE_CONFIDENCE} quarters of history: "
                    f"{len(unx):,} on {unx['cik'].nunique():,} companies. "
                    f"Largest deviations (for a human to read):"]
        for _, r in unx.reindex(unx["deviation_x"].abs().sort_values(ascending=False).index).head(12).iterrows():
            out.append(f"  {int(r['cik']):>8} {str(r['name'])[:34]:<34} {r['label']:<12} "
                       f"{r['shares']:>18,.0f} vs level {r['level']:>15,.0f} "
                       f"({r['deviation_x']:,.1f}x, {int(r['level_confidence'])} quarters)")
    ls = flagged[flagged["continuity_label"] == "level_shift"]
    out += ["", f"level shifts kept by the series (corporate actions, NOT repaired): {len(ls):,} on "
                f"{ls['cik'].nunique():,} companies"]
    return "\n".join(out)


COMPANY_FILE = "output/company_ownership_by_quarter.csv"


def published_impact(c: pd.DataFrame) -> tuple[str, dict, pd.DataFrame]:
    """What the series says about the figures that were actually PUBLISHED.

    The company file carries one denominator per company-quarter; this panel carries one per class.
    Comparing the published denominator with the sum of the company's own class levels is the only
    way the data itself can say "the denominator you published is not the one your history
    supports". It is how the Central Garden & Pet family of errors surfaced: 296% published against
    a 12.2M denominator while the company's own panel also carries a 35.4M Class A series."""
    if not Path(COMPANY_FILE).exists():
        return f"{COMPANY_FILE} absent: published impact not measured", {}, c.iloc[0:0]
    co = pd.read_csv(COMPANY_FILE)
    co["quarter_end"] = pd.to_datetime(co["quarter_end"])
    lv = c.groupby(["cik", "quarter_end"]).agg(
        level_sum=("level", "sum"), level_max=("level", "max"), n_classes=("class_axis", "nunique"),
        confidence=("level_confidence", "max"),
        flagged=("continuity_label", lambda s: int((~s.isin(["ok", "no_history", "no_usable_level"])).sum())),
    ).reset_index()
    m = co.merge(lv, left_on=["company_cik", "quarter_end"], right_on=["cik", "quarter_end"], how="left")
    pub = m[m["institutional_ownership_pct"].notna() & m["level_sum"].notna() & (m["level_sum"] > 0)].copy()
    pub["published_over_level"] = pub["shares_outstanding"] / pub["level_sum"]
    # the denominator its own history contradicts by a power of ten, with real history behind it
    contra = pub[((pub["published_over_level"] >= 100) | (pub["published_over_level"] <= 0.01))
                 & (pub["confidence"] >= ACTIONABLE_CONFIDENCE)]
    # The band the 300% ceiling does not catch: a figure over 100% published against a denominator
    # SMALLER than another share class of the same company in the same quarter. The test is the
    # single class level, not the sum: summing class series double counts, because a company's
    # panel often carries the same class three ways (Central Garden & Pet appears undimensioned,
    # as CommonStock and as CommonClassOne, all ~12.2M). "A bigger class exists" needs no
    # assumption about which series are the same thing, so it is the version that can be defended.
    # 0.8, not 1.0: the same class filed at two vintages differs by a percent or two, and Contango
    # Oil & Gas (denominator 15,194,952 against a largest class of 15,259,724) is that, not a class
    # mismatch. A denominator a fifth smaller than a class of the same company is not a vintage.
    pub["published_over_max_class"] = pub["shares_outstanding"] / pub["level_max"]
    # Only a denominator CLAIMING to be the company total can be contradicted by a larger class.
    # Since decision 15 a denominator may be deliberately class-scoped (denominator_basis
    # single_class_matched or classes_combined), and those are smaller than an unheld class as a
    # matter of definition, not defect - counting them took this measure from 133 to 160 while the
    # build got better, which is how a metric stops measuring what it is named after.
    basis = pub["denominator_basis"].fillna("single_class_held") if "denominator_basis" in pub \
        else pd.Series("single_class_held", index=pub.index)
    band = pub[(pub["institutional_ownership_pct"] > 100) & (pub["published_over_max_class"] <= 0.8)
               & (pub["n_classes"] > 1) & (pub["confidence"] >= ACTIONABLE_CONFIDENCE)
               & basis.isin(["single_class_held", "undimensioned_total"])]
    met = {"published_matched": int(len(pub)),
           "published_contradicted_100x": int(len(contra)),
           "published_over_100_smaller_than_a_class": int(len(band)),
           "published_over_100_total": int((pub["institutional_ownership_pct"] > 100).sum())}
    out = ["", "PUBLISHED FIGURES, judged against each company's own history",
           f"  matched to a level: {len(pub):,} of "
           f"{int(co['institutional_ownership_pct'].notna().sum()):,} published figures",
           f"  denominator contradicted by >= 100x with >= {ACTIONABLE_CONFIDENCE} quarters of "
           f"history: {len(contra):,}",
           f"  figures above 100% whose denominator claims to be the company total and is at most "
           f"0.8x another share class of the same company that quarter: {len(band):,} of "
           f"{met['published_over_100_total']:,} published figures above 100%",
           f"  (the sum of a company's class levels is an upper bound, not its total: the same "
           f"class often appears more than once in the panel)"]
    if len(band):
        out.append("  largest (published % | denominator used | largest class level | classes):")
        for _, r in band.sort_values("institutional_ownership_pct", ascending=False).head(12).iterrows():
            out.append(f"    {int(r['company_cik']):>8} {str(r['company_name'])[:30]:<30} "
                       f"{r['quarter_end'].date()}  {r['institutional_ownership_pct']:7.1f}%  "
                       f"{r['shares_outstanding']:>14,.0f}  {r['level_max']:>14,.0f}  "
                       f"{int(r['n_classes'])}")
    return "\n".join(out), met, band


def run(labels: list[str] | None = None, quiet: bool = False) -> pd.DataFrame:
    c = classify(panel(labels))
    Path("output/problems").mkdir(parents=True, exist_ok=True)
    Path("cache/parsed").mkdir(parents=True, exist_ok=True)
    cols = ["cik", "name", "class_axis", "label", "quarter_end", "shares", "n_quarters", "level",
            "level_before", "level_after", "level_confidence", "deviation_x", "shift_x", "continuity_label",
            "scale_factor", "shares_repaired", "tag", "shares_outstanding_source",
            "shares_outstanding_date", "scale_corrected"]
    c[cols].to_parquet(PARQUET, index=False)
    flagged = c[~c["continuity_label"].isin(["ok", "no_history", "no_usable_level"])]
    flagged[cols].sort_values(["continuity_label", "cik", "quarter_end"]).to_csv(REPORT_CSV, index=False)
    imp_txt, imp_met, band = published_impact(c)
    txt = report(c) + "\n" + imp_txt
    Path(REPORT_TXT).write_text(txt + "\n")
    if len(band):
        band_cols = ["company_cik", "company_name", "quarter_end", "institutional_ownership_pct",
                     "shares_held_total", "shares_outstanding", "level_max", "level_sum",
                     "published_over_max_class", "n_classes", "n_cusips", "denominator_basis",
                     "over_100_cause", "shares_outstanding_source"]
        band.reindex(columns=band_cols).sort_values("institutional_ownership_pct", ascending=False) \
            .to_csv(BAND_CSV, index=False)
    # metrics for pipeline/validate.py, so the properties are checked without rebuilding the panel
    met = {k: int(v) for k, v in c["continuity_label"].value_counts().items()}
    met.update(imp_met)
    met["observations"] = int(len(c))
    met["series"] = int(c.groupby(["cik", "class_axis"]).ngroups)
    met["quarters"] = int(c["label"].nunique())
    met["repairs_proposed"] = int(c["shares_repaired"].notna().sum())
    Path(METRICS).write_text(json.dumps(met, indent=2, sort_keys=True) + "\n")
    print(txt if not quiet else txt.splitlines()[0])
    print(f"\nwrote {REPORT_TXT}, {REPORT_CSV} ({len(flagged):,} flagged rows), "
          f"{BAND_CSV} ({len(band):,} rows), {PARQUET}, {METRICS}")
    return c


if __name__ == "__main__":
    sys.path.insert(0, ".")
    run(quiet="--quiet" in sys.argv)
