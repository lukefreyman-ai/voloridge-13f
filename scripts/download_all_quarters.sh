#!/bin/zsh
# Background pre-fetch of every configured quarter except the two pilots. Download only, low rate
# (EDGAR_RATE=3 of the 10 req/s SEC budget) so foreground jobs can keep fetching. Run under caffeinate.
cd ~/voloridge-13f
export EDGAR_RATE=3 EDGAR_WORKERS=2
for yq in "2010 3" "2010 4" "2011 1" "2011 2" "2011 3" "2011 4" "2012 1" "2012 2" "2012 3" "2012 4" "2013 1" "2013 2" "2013 3" "2013 4" "2014 2" "2014 3" "2014 4" "2015 1"; do
  y=${yq% *}; q=${yq#* }
  echo "=== $(date '+%F %T') index $y Q$q"
  python3 -m pipeline.run download $y $q || echo "FAILED $y $q"
done
echo "=== $(date '+%F %T') all downloads finished"
