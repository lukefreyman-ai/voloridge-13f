#!/bin/zsh
# Stage 2-4 for the 18 non-pilot quarters (Luke 2026-10-15), same rules as the pilots. Per quarter, in order:
#   13G/13D filings of the period + index quarter (download, cached ones skipped) -> sc13 parse -> the two XBRL notes
#   sets (curl, skipped if present) -> CUSIP->CIK resolve -> shares outstanding (XBRL, then the approved 10-K regex
#   fallback) -> ownership -> what-if -> hand check (20) -> commit. A failed step logs and moves to the next quarter.
# Then the 2013Q4 tripwire (resolve + ownership re-run on pilot_2013Q4, md5 compared) and the summary table.
# Resume: re-run the script; quarters with hand_check.txt are skipped. Log: logs/stage234_driver.log
set -u
cd ~/voloridge-13f
export EDGAR_RATE=${EDGAR_RATE:-8} EDGAR_WORKERS=${EDGAR_WORKERS:-4}
UA="Luke Freyman your-name your-email@example.com"
NOTES_BASE="https://www.sec.gov/files/dera/data/financial-statement-notes-data-sets"
QUARTERS=(2010Q2 2010Q3 2010Q4 2011Q1 2011Q2 2011Q3 2011Q4 2012Q1 2012Q2 2012Q3 2012Q4 2013Q1 2013Q2 2013Q3 2014Q1 2014Q2 2014Q3 2014Q4)
MAP_2013Q4_MD5=5bc4bc3172eb514bbe2edda81b7a9205      # data/pilot_2013Q4_cusip_cik_map.csv, 2026-10-15
CSV_2013Q4_MD5=2bc8b420284b14b169f72cb16c30017e      # output/pilot_2013Q4_institutional_ownership.csv, 2026-10-15
t() { date +%T; }
notes_get() {   # $1 = local path; skip if present and a valid zip
  local p=$1 name=${1:t}
  [ -s "$p" ] && unzip -tq "$p" >/dev/null 2>&1 && return 0
  local free_gb=$(df -g . | awk 'NR==2{print $4}')
  [ "$free_gb" -lt 3 ] && { echo "$(t) STOP: only ${free_gb} GB free, not downloading $name"; return 1; }
  echo "$(t) downloading $name"
  # resume a partial transfer and retry: these are 300-500 MB files and a single
  # failed attempt cost 2014Q3 a whole quarter on 2026-10-17
  curl -sS -L -A "$UA" --retry 5 --retry-delay 10 --retry-all-errors -C - \
       --connect-timeout 30 -o "$p.part" "$NOTES_BASE/$name" \
    && unzip -tq "$p.part" >/dev/null 2>&1 && mv "$p.part" "$p" && return 0
  echo "$(t) notes download FAILED: $name"; rm -f "$p.part"; return 1
}
gitcommit() {
  local msg="$1"; shift
  for i in {1..30}; do
    if [ ! -e .git/index.lock ]; then git add "$@" 2>/dev/null; git commit -q -m "$msg" && return 0; return 1; fi
    sleep 5
  done
  echo "git commit failed after retries: $msg" >&2; return 1
}
for q in $QUARTERS; do
  if [ -f output/problems/$q/hand_check.txt ]; then echo "$(t) $q already done, skipping"; continue; fi
  eval "$(python3 -m pipeline.quarters --env $q)"
  echo "$(t) === $q (index ${Q_IY}Q${Q_IQ}, 13G/13D $Q_SC13, notes ${Q_NOTES1:t} ${Q_NOTES2:t}) ==="
  L=logs/stage234_$q.log; : > $L
  python3 -m pipeline.sc13 download $Q_PY $Q_PQ $Q_IY $Q_IQ >> $L 2>&1 || { echo "$(t) $q sc13 download FAILED"; continue; }
  if [ ! -f cache/parsed/${Q_SC13}_sc13_links.parquet ]; then
    python3 -m pipeline.sc13 parse $Q_SC13 $Q_PY $Q_PQ $Q_IY $Q_IQ >> $L 2>&1 || { echo "$(t) $q sc13 parse FAILED"; continue; }
  fi
  notes_get $Q_NOTES1 >> $L 2>&1 || { echo "$(t) $q notes 1 missing"; continue; }
  notes_get $Q_NOTES2 >> $L 2>&1 || { echo "$(t) $q notes 2 missing"; continue; }
  mkdir -p output/problems/$q
  python3 -m pipeline.cusip_cik_resolve $q $Q_SC13 $Q_QEND $Q_PY $Q_PQ >> $L 2>&1 || { echo "$(t) $q cusip_cik_resolve FAILED"; continue; }
  python3 -m pipeline.shares_out build $q $Q_QEND $Q_NOTES1 $Q_NOTES2 >> $L 2>&1 || { echo "$(t) $q shares_out FAILED"; continue; }
  python3 -m pipeline.shares_out_regex $q $Q_QEND >> $L 2>&1 || { echo "$(t) $q shares_out_regex FAILED"; continue; }
  python3 -m pipeline.ownership $q $Q_QEND $Q_PERIOD >> $L 2>&1 || { echo "$(t) $q ownership FAILED"; continue; }
  python3 scripts/ownership_whatif.py $q $Q_QEND >> $L 2>&1 || echo "$(t) $q whatif FAILED"
  python3 scripts/hand_check.py $q 20 >> $L 2>&1 || echo "$(t) $q hand_check FAILED"
  echo "$(t) $q done: $(grep -h 'large companies (top 500' output/problems/$q/ownership_report.txt)"
  gitcommit "Stage 2-4 $q: 13G/13D map, shares outstanding (XBRL + 10-K regex), ownership, what-if, hand check" \
    output/problems/$q data/${q}_cusip_cik_map.csv data/${q}_name_match_review.csv $L scripts/run_stage234.sh pipeline/quarters.py
done
echo "$(t) === 2013Q4 tripwire: resolve + ownership re-run on pilot_2013Q4 ==="
python3 -m pipeline.cusip_cik_resolve pilot_2013Q4 sc13_2013 2013-12-31 2013 4 > logs/stage234_tripwire.log 2>&1
python3 -m pipeline.ownership pilot_2013Q4 2013-12-31 20131231 >> logs/stage234_tripwire.log 2>&1
m1=$(md5 -q data/pilot_2013Q4_cusip_cik_map.csv); m2=$(md5 -q output/pilot_2013Q4_institutional_ownership.csv)
[ "$m1" = "$MAP_2013Q4_MD5" ] && echo "$(t) tripwire map: unchanged" || echo "$(t) TRIPWIRE: pilot_2013Q4 map CHANGED ($m1)"
[ "$m2" = "$CSV_2013Q4_MD5" ] && echo "$(t) tripwire ownership CSV: unchanged" || echo "$(t) TRIPWIRE: pilot_2013Q4 ownership CSV CHANGED ($m2)"
python3 scripts/stage4_table.py > logs/stage4_table.log 2>&1 && cat logs/stage4_table.log
gitcommit "Stage 2-4: 2013Q4 tripwire re-run + stage4 summary table" output/problems/stage4_table.csv output/problems/stage4_table.txt output/problems/pilot_2013Q4 logs/stage234_tripwire.log logs/stage4_table.log
echo "$(t) STAGE 2-4 DONE"
