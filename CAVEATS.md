# Caveats: how to use this dataset, and how not to

Read this before using any number in `output/`. Written 2026-10-18 after an external-style
review. Every figure cited here comes from a file named beside it; nothing is typed by hand.

## 1. The ownership percentage is a company-level figure

`institutional_ownership_pct` is defined by the project description as *total shares reported by
institutional investors / shares outstanding*. That is a **company-quarter** quantity. In the
row-level file (`institutional_ownership_12col.csv`, one row per manager per security) the same
company figure is repeated on every one of that company's rows.

- A single row's `shares_held / shares_outstanding` is **not** this column and will not match it.
- **Never sum or average `institutional_ownership_pct` across rows.** You will multiply it by the
  number of managers.
- Use **`company_ownership_by_quarter.csv`** instead. One row per company-quarter, which is the
  variable's real grain, and it carries the quality flags including `denominator_basis`.
- The row-level `shares_outstanding` is the count for **that row's share class**, which for a
  dual-class company is not the company denominator. `company_shares_outstanding` on the same row
  is the company one, and it is the one `institutional_ownership_pct` was computed from.

## 2. The panel is not comparable across quarters without conditioning

Four construction changes move the measured level for reasons that are not market events. This is
the most important limitation in the dataset.

| Break | What changes | Where to see it |
|---|---|---|
| **2011Q1: XBRL phase-in** | Companies with a usable shares-outstanding fact jump roughly 1,600 to 6,700. XBRL was phased in largest-filers-first, so 2010 is a large-cap sample and 2014 is near-complete. Ownership is size-correlated | `output/problems/<q>/shares_out.txt` |
| **Every Q2/Q3: identity map thins** | The CUSIP-to-company map is built from Schedule 13G/13D filings, which cluster around the 14 February annual deadline. Q1 and Q4 labels get roughly 5,500 filing-derived links; Q2 and Q3 get roughly 1,700 and fall back to name matching. Unidentified-issuer rows run about 2 to 15% in Q1/Q4 against about 11 to 22% in Q2/Q3 | `data/<q>_cusip_cik_map.csv` |
| **2012Q3: security universe** | Distinct CUSIPs fall about 22% (34,891 to 27,217) while row count rises, driven by debt-convention CUSIPs falling from 6,014 to 792. Distinct-security counts are not comparable across this boundary | `output/problems/<q>/ownership_report.txt` |
| **2013Q2: parser regime** | Filings switch from free text to structured XML (`xml%` 0 to 100). Parse pass rates rise and parse errors fall to zero. The numerator is produced by a different code path before and after | `output/problems/all_quarters_table.csv` |

**Consequence, measured:** the median ownership trend 2010 to 2014 is slightly **down** on the raw
sample and clearly **up** on a fixed panel of companies present in all 20 quarters. The sign of the
headline trend depends on composition. Sample size and measured median are negatively correlated.

**If you need a time series:** restrict to companies with a denominator in every quarter you use,
or condition on denominator availability, map source and parse regime. Do not take the raw
cross-quarter medians as a trend.

## 3. Denominator vintage

`shares_outstanding` comes from XBRL facts in the SEC Financial Statement and Notes data sets.
As of 2026-10-18 the pipeline picks the fact whose as-of date is **nearest the quarter end**,
whichever tag carries it. Distance comes first: a stale balance-sheet figure is worse than a near
cover-page one. Where two facts tie on distance, the balance-sheet tag
(`CommonStockSharesOutstanding`, dated at period end) wins over the cover-page tag
(`EntityCommonStockSharesOutstanding`, dated near the filing date).

- Before that change the denominator was a median 90 days **after** the quarter end, which is
  lookahead. Any figure published before 2026-10-18 carries it.
- `shares_outstanding_source` names the form, accession and XBRL tag used for every row, so the
  vintage of each denominator is checkable.
- Gaps over 100 days are flagged. `shares_outstanding_date` is in every row: **if you need
  point-in-time discipline, filter on it yourself.** The dataset has an as-of date but no separate
  knowledge date, so it is not backtestable as shipped without that filter.

## 3b. Two denominator guards, and what they suppress

Some XBRL share-count facts are tagged in **thousands** and the SEC data set stores them verbatim.
Apple 2014Q1 carries a balance-sheet count of 861,745 against a cover-page 861,381,000. Two guards
catch this:

1. **Cross-check between tags.** Where both the balance-sheet and cover-page facts exist, a fact is
   replaced by the other one only when the ratio between them is consistent with a thousands-tagging
   error (900x to 1100x) **and** the result is a possible share count for a US listed company. The
   test runs in both directions: a fact can be 1,000x too small (Apple) or 1,000x too large
   (Pentair, which published 9.84e10 shares against a real ~1e8). An earlier version took the larger
   fact whenever the two differed by more than 10x, which fired on genuine reverse splits and, where
   the other fact was the broken one, took the broken one: Oracle 2012Q2 published 4.819e15 shares
   that way. 7 to 112 facts per quarter are corrected, and `shares_outstanding_source` marks them
   `(scale-corrected)`.
2. **A relative ceiling of 300%.** The cross-check only fires when both tags exist. Where only one
   does and it is scaled, nothing catches it on absolute grounds: Simon Property 2012Q4 shows 8,000
   shares outstanding and Abercrombie 87,846, both 1000x too small. Measured over the 69,984
   published company-quarters the distribution is p99 = 114%, p99.5 = 124%, p99.9 = 200%. Securities
   lending double-reports a holding; it does not produce 300%. **Above 300% the figure is suppressed,
   not published**, and `pct_suppressed_cause` records why: `shares_outstanding_scale_suspect` (88),
   or `multi_cusip_classes_summed` where the company has more than one CUSIP (39, see section 5).

127 company-quarters are suppressed by the ceiling, 0.18% of the 69,984 that have a figure. A
further 633 are withheld because the denominator cannot be made to cover the classes held (section
5). All of them keep their `shares_outstanding` value so the error is inspectable, and none is
deleted.

A third guard sits across the quarters rather than inside one: `pipeline/continuity.py` reads each
company's own 20-quarter share-count history and labels any observation its own series contradicts.
It is a diagnostic, not yet merged into the denominator - `output/problems/continuity_shares_out.txt`
and `continuity_metrics.json` carry its findings, and `pipeline/validate.py` enforces seven
properties of its rules.

## 4. Ownership above 100% is reported, not capped

This is deliberate. Capping would hide the evidence. Documented causes, annotated per company in
`output/problems/<q>/over_100_companies.csv`:

1. **Securities lending.** Lent shares can be reported by both the lender and the borrower's buyer.
   This is a real market mechanism, not an error. It is **not quantified**: no borrow or
   short-interest series has been brought in to test it.
2. **Multiple CUSIPs summed.** Where two CUSIPs of the same share class map to one issuer the
   numerator sums them, and 99 published figures above 100% still rest on a company-total
   denominator smaller than a class of that company. Different classes are now combined properly,
   and warrants, dated units and preferred no longer enter the numerator at all. See sections 5
   and 6.
3. **Denominator timing.** Largely addressed by the 2026-10-18 change; see section 3.

A residual carries **no identified cause** and is labelled that way. Testing and correcting the
denominator vintage did **not** reduce the over-100% rate, which is evidence the residual is not a
vintage artifact. Treat an unexplained excess as a construction artifact until shown otherwise.

## 5. Share classes

The rule is that the denominator must cover the same share classes the numerator sums (decision 15,
2026-10-21). Which classes a company's institutions hold is read from the SEC's own 13(f) list
description (`COM`, `CL A`, `CL B`), so coverage is checked against the filing universe rather than
assumed. `denominator_basis` on every row and in the company file says which of these applied:

| basis | published figures | meaning |
|---|---|---|
| `single_class_held` | 67,075 | one class held and the company total is known: the total is the denominator |
| `single_class_matched` | 2,408 | one class held, and the undimensioned count is smaller than that class so it cannot be the total, or there is no undimensioned count at all: the class's own count is used |
| `classes_combined` | 430 | more than one class held and each has a count: they are summed |
| `undimensioned_total` | 71 | the undimensioned count agrees with the class facts' sum, so it already includes them |

Where a held class has no count of its own, no figure is published and `pct_suppressed_cause` names
the class: **621 company-quarters**, plus **12** where the data cannot say whether an undimensioned
count is a company total or one large class (`denominator_coverage_ambiguous`).

**What this replaced.** Until 2026-10-21 the company figure was published whenever a company
reported an undimensioned count, even when the institutions held two classes and that count covered
one of them. Central Garden & Pet 2013Q4 published 275.2%: 33,700,786 shares held across its COM
(153527106) and CL A (153527205) CUSIPs over an undimensioned 12,246,751, while its own Class A fact
that quarter was 35,423,560. It now reads 70.7% against the combined 47,670,311, with per-class
figures of 58.0% and 75.1% in `class_ownership_pct`. 133 published figures between 100% and 296%
were this. The defect was found by `pipeline/continuity.py`, which reads each company's own 20
quarters, not by inspecting any one quarter.

**What remains, measured.** **5,631 of 69,984 published figures (8.0%, median 71.7%)** still have
`n_cusips > 1`. These are companies holding more than one CUSIP of the *same* class key: a second
`COM` line, a `COM NEW` after a reorganisation, or a CUSIP absent from that quarter's 13(f) list
(the list is parsed from the SEC's PDF, and an unlisted CUSIP has no class description to read). Of
those, **99 are published above 100% while a class of the same company is at least a fifth larger
than the denominator used** - the residual of the original defect, listed with its evidence in
`output/problems/continuity_published_over_100.csv`. United Community Banks 2011Q1 is the shape:
three CUSIPs mapped to the CIK, two of them unlisted and almost certainly preferred series, all
summed over the common count. Treat any company with `n_cusips > 1` as possibly class-mixed.

Berkshire Hathaway, the obvious dual-class case, is not affected: its figure is withheld in all 20
quarters, suppressed in 2010 and `multi_class_flag` from 2011Q2 onward.

## 6. What is excluded from the ownership figure

Rows are kept in the output and flagged, never deleted. `excluded_from_ownership` says why:

- `debt_cusip` fixed income (letter in CUSIP position 7)
- `derivative_cusip` derivative or non-standard lines (position 7 is 9)
- `adr` ADR and ADS lines
- `warrant_or_right` warrants and rights ("*W EXP 12/19/201", "RIGHT 99/99/9999"): not shares
- `dated_unit` a unit with an expiry date ("UNIT 99/99/9999") is a SPAC unit, one share bundled
  with a warrant. Undated units are NOT excluded: "COM UNIT LP", "UNIT LTD PARTN" and "SH BEN INT"
  are the actual equity of a partnership or trust
- `preferred` preferred stock ("6.50% PFD CUM CO", "CV PFD-E 7.25%"), which has its own share count
  and is never part of common shares outstanding
- `shares_outstanding_implausible` denominator outside [1,000, 35,000,000,000] shares
- `holding_exceeds_shares_outstanding` one manager reporting more shares than exist, which is a
  units error in the filing. Tested twice: against the company count, and again against the
  class-scoped denominator actually published on the row (decision 15 made those different numbers)

The three security-type exclusions were added 2026-10-21 with the same reasoning as the ADR rule:
they are not the common stock they were being divided by. Chart Acquisition Corp 2014Q1 is the
case. 571,003 common shares held of 3,566,447 outstanding is 16%, but 250,000 units and 403,498
warrants were being added to the numerator, which published it at 296.8% - the highest figure in
the build before this change.

ETFs, closed-end funds and unit trusts are excluded as **securities** (about 5% of 13F value,
`output/<q>_excluded_funds.csv`); fund managers are correctly retained as **holders**. The fund
classifier is presence-based over 2010 to 2015 and therefore time-invariant, which is a mild
look-ahead in classification.

## 7. Validation coverage

The exact row-level match against the SEC's own structured 13F data set
(`output/problems/pilot_2013Q4/secds_compare.txt`) is real, but the SEC data set begins 2013Q2 and
every quarter it covers is 100% XML. **It therefore validates none of the 13 text-era quarters**,
which is where the parsing difficulty lives. The match key is (CUSIP, shares, value) and does not
include the SH/PRN or put/call fields that the ownership filter runs on.

## 8. Numerator inclusion rule

Rows are included when `sh_prn != "PRN"`, which includes rows where the field is **blank**. In the
text era roughly 100,000 rows a quarter are blank rather than explicitly "SH". Explicit PRN is
about 1% of rows, so expected contamination is small, but a principal amount reported in the share
field would be large where it occurs. The `holding_exceeds_shares_outstanding` gate in section 6
catches the extreme cases.

## 8b. Which outputs are in the repository

In the repository: `output/company_ownership_by_quarter.csv` (13 MB, the company-quarter file),
`output/deliverable_manifest.json`, and the per-quarter reports under `output/problems/`.

Shared through Google Drive, being too large for GitHub: the row-level
`institutional_ownership_12col.csv` (2.8 GB) and the per-quarter 31-column
`<quarter>_institutional_ownership.csv` and `<quarter>_excluded_funds.csv` files. Any citation of
those in this document refers to the Drive copy or to a local build.

## 9. Provenance

`output/deliverable_manifest.json` records the build time, the code commit and, per quarter, the
source file, size and modification time. If `single_build_date` is false the per-quarter files come
from more than one run and the concatenated file is a mixed vintage. Check it before citing any
figure.
