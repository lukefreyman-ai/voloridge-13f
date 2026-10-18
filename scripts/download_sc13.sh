#!/bin/zsh
# Stage 2: SC 13G/13D filings for the two pilots. EDGAR_RATE=5 alongside the 18-quarter download at 3 => 8 req/s.
cd ~/voloridge-13f
export EDGAR_RATE=5 EDGAR_WORKERS=4
python3 -m pipeline.sc13 download 2010 1 2010 2 2014 1 2013 4
echo "=== $(date '+%F %T') sc13 downloads finished"
