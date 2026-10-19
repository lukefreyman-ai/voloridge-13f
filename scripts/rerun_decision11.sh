#!/bin/zsh
# Decision 11: re-run shares outstanding + ownership for every quarter with the new denominator
# preference (period-end balance-sheet fact first). Parsing is untouched, so checksum/parse rates
# cannot move; what moves is the denominator, coverage and the over-100% counts.
set -u
cd ~/voloridge-13f
for q in pilot_2010Q1 2010Q2 2010Q3 2010Q4 2011Q1 2011Q2 2011Q3 2011Q4 2012Q1 2012Q2 2012Q3 2012Q4 2013Q1 2013Q2 2013Q3 pilot_2013Q4 2014Q1 2014Q2 2014Q3 2014Q4; do
  eval "$(python3 -m pipeline.quarters --env $q)"
  L=logs/d11_$q.log; : > $L
  echo "$(date +%T) === $q"
  python3 -m pipeline.shares_out build $q $Q_QEND $Q_NOTES1 $Q_NOTES2 >> $L 2>&1 || { echo "  shares_out FAILED"; continue; }
  python3 -m pipeline.shares_out_regex $q $Q_QEND >> $L 2>&1 || echo "  regex fallback FAILED"
  python3 -m pipeline.ownership $q $Q_QEND $Q_PERIOD >> $L 2>&1 || { echo "  ownership FAILED"; continue; }
  grep -h 'large companies (top 500' output/problems/$q/ownership_report.txt | sed 's/^/  /'
done
echo "$(date +%T) DECISION 11 RERUN DONE"
