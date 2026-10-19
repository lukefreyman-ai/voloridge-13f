#!/bin/zsh
set -u
cd ~/voloridge-13f
for q in pilot_2010Q1 2010Q2 2010Q3 2010Q4 2011Q1 2011Q2 2011Q3 2011Q4 2012Q1 2012Q2 2012Q3 2012Q4 2013Q1 2013Q2 2013Q3 pilot_2013Q4 2014Q1 2014Q2 2014Q3 2014Q4; do
  eval "$(python3 -m pipeline.quarters --env $q)"
  echo "$(date +%T) $q"
  python3 -m pipeline.ownership $q $Q_QEND $Q_PERIOD > logs/ceiling_$q.log 2>&1 \
    && grep -hE 'OWNERSHIP CEILING|large companies \(top 500' output/problems/$q/ownership_report.txt | sed 's/^/  /' \
    || echo "  FAILED"
done
echo "$(date +%T) CEILING RERUN DONE"
