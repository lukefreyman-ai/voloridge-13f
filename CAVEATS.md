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
  variable's real grain, and it carries the quality flags.

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

1. **Cross-check between tags.** Where both the balance-sheet and cover-page facts exist and differ
   by more than 10x, the larger is used, because a listed company's share count cannot genuinely
   move that far in a quarter. 8 to 149 facts per quarter are corrected this way, and
   `shares_outstanding_source` marks them `(scale-corrected)`.
2. **A relative ceiling of 300%.** The cross-check only fires when both tags exist. Where only one
   does and it is scaled, nothing catches it on absolute grounds: Simon Property 2012Q4 shows 8,000
   shares outstanding and Abercrombie 87,846, both 1000x too small. Measured over 67,672
   company-quarters the distribution is p99 = 118%, p99.5 = 147%, p99.9 = 395%. Securities lending
   double-reports a holding; it does not produce 300%. **Above 300% the figure is suppressed, not
   published**, and `pct_suppressed_cause` records why: `shares_outstanding_scale_suspect`, or
   `multi_cusip_classes_summed` where the company has more than one CUSIP (see section 5).

135 company-quarters are suppressed: 0.20% of the 67,672 that had a figure, 0.15% of all
88,608 rows in the company file. They keep their `shares_outstanding` value so the
error is inspectable, and they are not deleted.

## 4. Ownership above 100% is reported, not capped

This is deliberate. Capping would hide the evidence. Documented causes, annotated per company in
`output/problems/<q>/over_100_companies.csv`:

1. **Securities lending.** Lent shares can be reported by both the lender and the borrower's buyer.
   This is a real market mechanism, not an error. It is **not quantified**: no borrow or
   short-interest series has been brought in to test it.
2. **Multiple CUSIPs summed.** Where a company has several share classes or units mapped to one
   issuer, the numerator sums them. See section 5.
3. **Denominator timing.** Largely addressed by the 2026-10-18 change; see section 3.

A residual carries **no identified cause** and is labelled that way. Testing and correcting the
denominator vintage did **not** reduce the over-100% rate, which is evidence the residual is not a
vintage artifact. Treat an unexplained excess as a construction artifact until shown otherwise.

## 5. Share classes

The stated rule is that classes are never summed, and that holds for the per-class figure
(`class_ownership_pct`) and for companies whose XBRL facts are class-dimensioned, which get a null
company figure and `multi_class_flag`. But the **company-level** numerator sums every CUSIP mapped
to the issuer against a single undimensioned denominator. Where a company has more than one common
CUSIP and publishes an undimensioned fact, that figure mixes classes. Measured on the current
build: **6,684 of 67,537 published company figures (9.9%) have `n_cusips > 1`, median 72.7%** --
so most sit below 100% and no existing flag catches them. `n_cusips` in the company file shows how
many securities went into each figure: **treat any company with `n_cusips > 1` as class-mixed.**
Berkshire Hathaway, the obvious example, is *not* among them: its figure is withheld in all 20
quarters, suppressed in 2010 and `multi_class_flag` from 2011Q2. This is a known open decision, not a
silent defect.

## 6. What is excluded from the ownership figure

Rows are kept in the output and flagged, never deleted. `excluded_from_ownership` says why:

- `debt_cusip` fixed income (letter in CUSIP position 7)
- `derivative_cusip` derivative or non-standard lines (position 7 is 9)
- `adr` ADR and ADS lines
- `shares_outstanding_implausible` denominator outside [1,000, 100,000,000,000] shares
- `holding_exceeds_shares_outstanding` one manager reporting more shares than exist, which is a
  units error in the filing

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
