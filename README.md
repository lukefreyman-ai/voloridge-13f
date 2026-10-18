# Voloridge 13F institutional ownership, 2010-2014

Reads every SEC Form 13F filing from 2010 Q1 to 2014 Q4 and reports, per company, the
share of its stock held by institutional investors.

Luke Freyman, UCF FinTech M.S. Research project for Dr. Cuneyt Akcora. Due 2026-11-15.

## Terms

- Form 13F: quarterly SEC report filed by institutional managers holding over $100M in US
  stocks. Lists each holding: company, CUSIP, value, share count.
- CUSIP: 9-character security identifier. First 6 characters identify the issuer, next 2 the
  share class, last is a check digit.
- Shares outstanding: total shares a company has issued. The denominator for ownership, taken
  from the company's own filings.
- Value: dollar market value of a holding, as the manager reported it.
- Schedule 13G / 13D: filed when an investor crosses 5% ownership. Names both the CUSIP and
  the company, so these are the most reliable CUSIP-to-company source.
- XBRL: machine-readable tagging in SEC filings, universal from 2013.

## Scope

74,217 filings, 30,023,434 holdings rows. 7 of the 20 quarters are structured XML.
The other 13 are free-text documents with no schema: fixed-width tables, inconsistent
column order, per-filer layouts.

## Parse coverage

Share of reported dollar value that parses into usable rows and reconciles with the totals
the filer declared on its own cover page:

- Lowest quarter: 2011Q3, 86.3%
- Highest quarter: pilot_2013Q4, 99.5%
- All 20 quarters at or above 86.3%

Per quarter: `output/problems/all_quarters_table.csv`, column `pass+classA_plausible%`. That column counts rows
matching the filer's declared total exactly or within the documented class A tolerance. The
stricter `pass_value%` column is also present and falls to 13% in 2012 Q2, where several large
filers report value in thousands rather than units.

## Validation against SEC data

2013 Q4 is the earliest quarter with an SEC-published structured 13F data set. Compared row by
row:

- Row-level exact match on (CUSIP, shares, value): 1584855/1584855 = 100.000%
- Filings matching on row count, share total and value total: 4038/4038 = 100.00%
- Filings with any mismatch: 0

The match holds for filings our own checksum flags as failing, which locates those failures in
filer-side reporting (value in thousands, entry totals counting distinct CUSIPs rather than
rows) rather than in the parser. Breakdown: `output/problems/pilot_2013Q4/secds_compare.txt`.

Text-era quarters have no SEC reference set. Each filing is reconciled against its own declared
cover-page totals instead.

## Ownership results, pilot quarters

| | 2010 Q1 | 2013 Q4 |
|---|---|---|
| Holdings rows used | 1,034,768 | 1,289,567 |
| CUSIP to company, by value | 95.6% | 97.9% |
| Companies with shares outstanding | 2,488 / 4,967 = 50.1% | 3,937 / 4,633 = 85.0% |
| Same, by 13F value | 83.9% | 87.6% |
| Companies over 100% | 127 / 2,488 = 5.1% | 241 / 3,937 = 6.1% |
| Top 500 by value, over 100% | 14 = 3.5% | 28 = 6.7% |
| Fund CUSIPs excluded | 1,488 | 1,883 |

Rows used is a subset of rows parsed: common stock only, no puts or calls, CUSIP resolved,
share count above zero.

Median ownership is not comparable across quarters. It is computed only over companies that
have a shares-outstanding figure, and that denominator moves from 50% of companies in 2010 Q1
to 84% in 2012 Q1. Coverage weighted by value is stable at 83-88% across all quarters.

Ownership above 100% is reported, not capped. Documented causes, annotated per company in
`output/problems/<quarter>/over_100_companies.csv`:

1. Securities lending. Lent shares can be reported by both the lender and the borrower's buyer.
2. Timing. Shares outstanding comes from the next 10-K or 10-Q, up to 90 days later; buybacks
   in between shrink the denominator.
3. Data cases. Units, rights, or multiple classes mapping to one company. Flagged.

A residual has no identified data cause and is labelled as such.

## Decisions

- ETFs and investment funds excluded. Their shares outstanding are not comparable to an
  operating company's. 1,883 CUSIPs in 2013 Q4, about 5% of 13F value.
- Share classes never summed. Each class CUSIP is measured against that class's own shares
  outstanding; company-level percentage is null for multi-class companies rather than inferred.
- CUSIP to company mapping is evidence-first: Schedule 13G and 13D, then exact name matching
  against the SEC 13(f) securities list. Conflicts flagged, not resolved by guess.
  The limit of this method: a company only appears in 13G/13D if someone crossed 5% ownership
  of it, so companies with no 5% holder fall through to name matching or stay unmapped. That is
  why CUSIP-to-company coverage is 40-45% of companies but 96-98% of dollar value: the companies
  that fall through are small ones.
- Every parser rule is backed by a real filing kept as a test fixture, so a fix for one filer's
  layout cannot silently break another's. See `tests/` and `tests/FIXTURE_REVIEW.md`.

## Running

EDGAR requires a contact string. Set your own in `config.yaml` (`user_agent`) before any online run; the cached run below needs nothing.

```
python3 -m pytest tests -q
jupyter nbconvert --to notebook --execute --inplace notebook.ipynb
```

`notebook.ipynb` is the main deliverable. It imports from `pipeline/` only and runs with
`EDGAR_OFFLINE=1` against a local filing cache, so output is reproducible without a live SEC
fetch. Quarters are set in its config cell. `python3 -m pipeline.quarters` lists what each
quarter still needs.

## Layout

```
pipeline/       parsing and ownership code
tests/          42 tests, each backed by a real filing fixture
scripts/        stage drivers and one-off investigations
data/           CUSIP to CIK maps, name-match review files
output/         per-quarter metrics and problem reports
notebook.ipynb
```

Output CSVs and the filing cache are too large for GitHub and are shared by Google Drive. The
cache is roughly 10 GB; per-quarter ownership CSVs are roughly 40 MB each zipped.

## Open items

- Shares outstanding for 2010 incomplete, pending a data file.
- Stages 2-4 complete for 12 of 20 quarters.
- Four named filers with unusual layouts unparsed, documented.
