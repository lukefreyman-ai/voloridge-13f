# Voloridge 13F institutional ownership, 2010-2014

Reads every SEC **Form 13F** filing from 2010 Q1 through 2014 Q4 and reports, per company and
quarter, the share of its stock held by institutional investors.

Luke Freyman, UCF FinTech M.S. Research project for Dr. Cuneyt Akcora. Due 2026-11-15.

**Read `CAVEATS.md` before using any number here.** It states what this dataset can and cannot be
used for, and it is not boilerplate: the panel is not comparable across quarters without
conditioning, and that is the most important thing to know.

## Terms

- **Form 13F**: quarterly SEC report filed by institutional managers holding over $100M in US
  stocks. Lists each holding: company, CUSIP, value, share count.
- **CUSIP**: 9-character security identifier. First 6 characters identify the issuer, the next 2
  the share class, the last is a check digit.
- **Shares outstanding**: total shares a company has issued. The denominator for ownership, taken
  from the company's own 10-K or 10-Q.
- **Value**: dollar market value of a holding, as the manager reported it.
- **Schedule 13G / 13D**: filed when an investor crosses 5% ownership. These name both the CUSIP
  and the company, which makes them the most reliable CUSIP-to-company source. The limit: a company
  only appears if someone crossed 5%, so companies with no 5% holder fall through to name matching.
- **XBRL**: machine-readable tagging in SEC filings, universal from 2013.

## Scope

74,217 filings, 30,023,434 holdings rows, all 20 quarters complete. 7 of the 20 quarters are
structured XML; the other 13 are free-text documents with no schema, inconsistent column order and
per-filer layouts. The text era is where the work is.

## Parse coverage

Share of reported dollar value that parses into usable rows and reconciles with the filer's own
declared totals:

- Lowest quarter: **2011 Q3 at 86.3%**; highest: **2013 Q4 at 99.5%**

Per quarter: `output/problems/all_quarters_table.csv`, column `pass+classA_plausible%`.

**What that column does and does not count**, because the number is generous and you should know
why. It counts rows that match the filer's declared total exactly, plus "class A" filings, which
are ones where the parse is judged right and *the filer's own summary page is wrong* (value stated
in thousands, entry totals counting distinct CUSIPs rather than rows). It also **excludes from both
numerator and denominator** filings whose parsed value exceeds 3x the filer's declared total or
$2tn, on the grounds that those parsed values are corrupt and would dominate a value-weighted
average. In 2012 Q2 that exclusion is 79% of weighted value. The strict metric with nothing
excluded, `pass_value%`, is in the same file and bottoms out at **13.3%** in that quarter.

## Validation against SEC data

The SEC publishes its own structured 13F data set from **2013 Q2 onward**, which is seven of these
twenty quarters. One, 2013 Q4, has been compared row by row:

- Row-level exact match on (CUSIP, shares, value): **1,584,855 / 1,584,855 = 100.000%**
- Filings matching on row count, share total and value total: **4,038 / 4,038**
- Filings with any mismatch: **0**

The match holds even for filings this project's own checksum flags as failing, which locates those
failures in filer-side reporting rather than in the parser. Detail:
`output/problems/pilot_2013Q4/secds_compare.txt`.

**Two honest limits.** Every quarter the SEC data set covers is 100% XML, so this validates none of
the 13 text-era quarters, which is where the parsing risk lives. And the match key is (CUSIP,
shares, value); it does not include the SH/PRN or put/call fields that the ownership filter uses.
The other six available quarters have not been compared yet.

## Ownership results, the two most-checked quarters

| | 2010 Q1 | 2013 Q4 |
|---|---|---|
| Holdings rows used | 1,040,801 | 1,289,567 |
| CUSIP to company, by value | 95.6% | 97.9% |
| Companies with shares outstanding | 2,495 / 4,916 = 50.8% | 4,148 / 4,617 = 89.8% |
| Same, weighted by 13F value | 87.7% | 93.9% |
| Companies over 100% | 125 / 2,487 = 5.0% | 256 / 4,143 = 6.2% |
| Top 500 by value, over 100% | 16 / 407 = 3.9% | 25 / 433 = 5.8% |
| Fund CUSIPs excluded | 1,491 | 1,883 |

The top-500 denominator is the top-500 companies that *have* a percentage (407 and 433), not 500.
Across all 20 quarters that rate runs 1.7% to 9.4% and exceeds the project's own 5% review
threshold in 8 quarters.

**Do not compare medians across quarters.** Coverage of the denominator changes underneath them:
50.4% of companies in 2010 Q1 against 86.1% in 2013 Q4, and institutional ownership is
size-correlated. Weighted by value, coverage is stable at 85.6% to 90.9%. CUSIP-to-company coverage
runs 31% to 45% of companies and 78% to 98% of value, with the low end in Q2 and Q3 quarters where
the 13G/13D map thins. `CAVEATS.md` section 2 has the four reasons the panel shifts.

**Ownership above 100% is reported, never capped.** Causes are annotated per company in
`output/problems/<quarter>/over_100_companies.csv`: securities lending (lent shares can be reported
by both the lender and the borrower's buyer, a real market mechanism, not quantified here), timing,
and two CUSIPs of one share class mapped to one company. A residual carries no identified cause and
is labelled that way. Correcting the denominator's vintage did not reduce the rate, which is evidence
the residual is not a vintage artifact.

## Decisions

- **ETFs and investment funds are excluded as securities**, since their shares outstanding are not
  comparable to an operating company's. Fund managers are correctly retained as holders.
- **The denominator must cover the same share classes the numerator sums.** Which classes a
  company's institutions hold is read from the SEC's own 13(f) list description (`COM`, `CL A`,
  `CL B`), so coverage is checked against the filing universe rather than assumed. Where holdings
  span two classes with a count each, the counts are combined; where a held class has no count, no
  figure is published and the cause names the class (621 company-quarters); where a company total
  is known it stays the denominator even if only one class is held, because the figure is ownership
  of the company. `denominator_basis` records which applied on every row. 5,631 of 69,984 published
  figures (8.0%) still have `n_cusips > 1`: two CUSIPs of the *same* class key, usually a second
  common line or a CUSIP absent from that quarter's 13(f) list. `CAVEATS.md` section 5 has the
  measured residual.
- **CUSIP to company mapping is evidence-first**: Schedule 13G and 13D, then exact name matching
  against the SEC 13(f) list. Conflicts are flagged and resolved by a documented rule, the majority
  CIK by filing count with ties going to the CIK whose 10-K/10-Q filed nearest the quarter end.
  CIKs are never merged.
- **Warrants, dated (SPAC) units and preferred are not common stock** and do not enter the
  numerator; their rows stay in the output, flagged, as ADR and debt rows do. `CAVEATS.md` section 6
  lists every exclusion.
- **Every parser rule is backed by a real filing kept as a test fixture**, so a fix for one filer's
  layout cannot silently break another's. `tests/` holds 117 tests over 36 fixtures.
  `tests/FIXTURE_REVIEW.md` is generated from the parser's own output: it is a readable record of
  what the parser produced, not independent corroboration of it.
- **Denominator guards**: XBRL counts tagged in thousands are cross-checked against the other tag
  and corrected; counts outside [1,000, 100bn] shares are nulled; company figures above 300% are
  suppressed with a recorded cause. `CAVEATS.md` section 3b explains each.

## Deliverables

```
output/company_ownership_by_quarter.csv   88,608 company-quarters, 16 columns, 13 MB
                                          one row per company per quarter, with the quality flags.
                                          This is the grain the ownership figure actually has and
                                          what a quantitative user should consume.
output/institutional_ownership_12col.csv  15,129,195 rows, the project description's 12 columns,
                                          one row per manager per security. 2.8 GB, via Drive.
output/deliverable_manifest.json          build time, code commit, per-quarter vintages
CAVEATS.md                                limitations, in detail
```

The row-level file repeats the **company-level** percentage on every one of a company's rows. A
single row's `shares_held / shares_outstanding` is not that column. Never sum or average
`institutional_ownership_pct` across rows; use the company file.

## Running

```
python3 -m pytest tests -q                                          # 62 tests
jupyter nbconvert --to notebook --execute --inplace notebook.ipynb
```

`notebook.ipynb` is the main deliverable and produces the final CSV itself. It imports from
`pipeline/` only and runs with `EDGAR_OFFLINE=1` against a local filing cache, so results are
reproducible without a live SEC fetch. Its config cell runs the two most-checked quarters by
default; `python3 -m pipeline.quarters` lists what each of the 20 needs. The cache is about 13 GB
and is not in this repository.

## Layout

```
pipeline/       parsing, mapping, shares outstanding, ownership
tests/          62 tests over 36 real-filing fixtures
scripts/        stage drivers and report generators
data/           CUSIP to CIK maps and name-match review files
output/problems/  per-quarter metrics, problem reports and annotated over-100% cases
notebook.ipynb
CAVEATS.md
```

## Open items

- Shares outstanding for 2010 is incomplete (50.4% of companies, 85.6% by value) pending a data file.
- 974 filings across the 20 quarters yielded no rows, with 1,062 parse errors, all listed by
  accession in the per-quarter reports. Zero in the seven XML quarters.
- Six of the seven SEC-validatable quarters have not been compared yet.
- The panel's cross-quarter comparability is documented in `CAVEATS.md` but not repaired.
