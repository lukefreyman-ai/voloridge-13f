#!/bin/zsh
# Task B (2026-10-11 overnight): parse the 18 non-pilot quarters with the CURRENT parser (no rule changes),
# then run the standard per-quarter checks in order, and commit after each quarter.
# Labels are report-period labels (2010Q2 = EDGAR index 2010Q3). Pilots (2010Q1, 2013Q4) are skipped.
# Worker cap: EDGAR_WORKERS=4 (Luke's limit while the clip pipeline runs).
set -u
cd ~/voloridge-13f
export EDGAR_WORKERS=4
export EDGAR_RATE=6
QUARTERS=(
 "2010 3 2010Q2" "2010 4 2010Q3" "2011 1 2010Q4"
 "2011 2 2011Q1" "2011 3 2011Q2" "2011 4 2011Q3" "2012 1 2011Q4"
 "2012 2 2012Q1" "2012 3 2012Q2" "2012 4 2012Q3" "2013 1 2012Q4"
 "2013 2 2013Q1" "2013 3 2013Q2" "2013 4 2013Q3"
 "2014 2 2014Q1" "2014 3 2014Q2" "2014 4 2014Q3" "2015 1 2014Q4"
)
gitcommit() {   # retry while another job holds the index lock
  local msg="$1"; shift
  for i in {1..30}; do
    if [ ! -e .git/index.lock ]; then
      git add "$@" && git commit -q -m "$msg" && return 0
    fi
    sleep 5
  done
  echo "git commit failed after retries: $msg" >&2; return 1
}
for q in "${QUARTERS[@]}"; do
  set -- ${=q}; y=$1; qq=$2; label=$3
  if [ -f "output/problems/$label/weighted_pass.txt" ]; then echo "$(date +%T) $label already done, skipping"; continue; fi
  echo "$(date +%T) === $label (index ${y}Q${qq}) ==="
  python3 -m pipeline.run $y $qq $label > logs/$label.log 2>&1 || { echo "$(date +%T) $label pipeline.run FAILED"; continue; }
  python3 -m pipeline.shares_check $label > logs/${label}_checks.log 2>&1 || echo "$(date +%T) $label shares_check FAILED"
  python3 scripts/failure_accounting.py $label >> logs/${label}_checks.log 2>&1 || echo "$(date +%T) $label failure_accounting FAILED"
  python3 scripts/triage_checksum.py $label >> logs/${label}_checks.log 2>&1 || echo "$(date +%T) $label triage FAILED"
  python3 scripts/big_filers.py $label 25 >> logs/${label}_checks.log 2>&1 || echo "$(date +%T) $label big_filers FAILED"
  python3 scripts/weighted_pass.py $label >> logs/${label}_checks.log 2>&1 || echo "$(date +%T) $label weighted_pass FAILED"
  echo "$(date +%T) $label done"
  gitcommit "Task B${RUN_TAG:-}: quarter $label parsed with the current parser + checksum/shares/triage reports" output/problems/$label logs/$label.log logs/${label}_checks.log scripts/run_remaining_quarters.sh
done
echo "$(date +%T) ALL QUARTERS DONE"
