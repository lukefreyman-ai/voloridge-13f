#!/bin/zsh
# Decision 12 (2026-10-18): full re-run of all 20 quarters after the review fixes.
# The amendment-checkbox fix is in the PARSER, so stage 1 must re-run too, not just ownership.
# Per quarter: parse from cache -> checksum reports -> CUSIP/CIK resolve -> shares outstanding
# -> ownership -> what-if -> hand check -> commit. EDGAR_OFFLINE so nothing can be downloaded.
set -u
cd ~/voloridge-13f
export EDGAR_OFFLINE=1
for q in pilot_2010Q1 2010Q2 2010Q3 2010Q4 2011Q1 2011Q2 2011Q3 2011Q4 2012Q1 2012Q2 2012Q3 2012Q4 2013Q1 2013Q2 2013Q3 pilot_2013Q4 2014Q1 2014Q2 2014Q3 2014Q4; do
  eval "$(python3 -m pipeline.quarters --env $q)"
  L=logs/d12_$q.log; : > $L
  echo "$(date +%T) === $q (index ${Q_IY}Q${Q_IQ})"
  python3 -m pipeline.run $Q_IY $Q_IQ $q                >> $L 2>&1 || { echo "  parse FAILED"; continue; }
  python3 -m pipeline.shares_check $q                   >> $L 2>&1 || echo "  shares_check FAILED"
  python3 scripts/failure_accounting.py $q              >> $L 2>&1 || true
  python3 scripts/triage_checksum.py $q                 >> $L 2>&1 || true
  python3 scripts/big_filers.py $q 25                   >> $L 2>&1 || true
  python3 scripts/weighted_pass.py $q                   >> $L 2>&1 || true
  python3 -m pipeline.cusip_cik_resolve $q $Q_SC13 $Q_QEND $Q_PY $Q_PQ >> $L 2>&1 || { echo "  resolve FAILED"; continue; }
  python3 -m pipeline.shares_out build $q $Q_QEND $Q_NOTES1 $Q_NOTES2  >> $L 2>&1 || { echo "  shares_out FAILED"; continue; }
  python3 -m pipeline.shares_out_regex $q $Q_QEND       >> $L 2>&1 || true
  python3 -m pipeline.ownership $q $Q_QEND $Q_PERIOD    >> $L 2>&1 || { echo "  OWNERSHIP FAILED (see $L)"; continue; }
  python3 scripts/ownership_whatif.py $q $Q_QEND        >> $L 2>&1 || true
  python3 scripts/hand_check.py $q 20                   >> $L 2>&1 || true
  grep -hE 'GRAIN|PLAUSIBILITY|large companies \(top 500' output/problems/$q/ownership_report.txt | sed 's/^/  /'
  git add output/problems/$q data/${q}_cusip_cik_map.csv data/${q}_name_match_review.csv $L 2>/dev/null
  git commit -q -m "Decision 12 re-run $q" 2>/dev/null || true
done
python3 scripts/quarter_summary.py > logs/d12_quarter_summary.log 2>&1 || true
python3 scripts/stage4_table.py    > logs/d12_stage4.log 2>&1 || true
echo "$(date +%T) DECISION 12 RERUN DONE"
