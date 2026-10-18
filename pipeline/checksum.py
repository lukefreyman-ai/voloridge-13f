"""Filing-level checksum status + cause. Exhaustive and mutually exclusive."""
from __future__ import annotations

import numpy as np
import pandas as pd

STATUS = ["pass", "fail_entries", "fail_value", "fail_both", "no_summary"]


def assign(filings: pd.DataFrame, holdings: pd.DataFrame) -> pd.DataFrame:
    derived = ["n_distinct_cusip", "entry_diff", "value_ratio", "checksum_status", "checksum_cause"]
    f = filings.drop(columns=[c for c in derived if c in filings]).copy()  # idempotent re-runs
    nd = holdings.groupby("accession")["cusip"].nunique().rename("n_distinct_cusip")
    f = f.merge(nd, left_on="accession", right_index=True, how="left")
    f["n_distinct_cusip"] = f["n_distinct_cusip"].fillna(0).astype(int)
    f["entry_diff"] = f["n_rows"] - f["entry_total"]
    f["value_ratio"] = (f["value_sum"] / f["value_total"].replace(0, np.nan)).astype(float)

    e_ok = f["checksum_entries_ok"]
    v_ok = f["checksum_value_ok"]
    status = np.select(
        [e_ok.isna() & v_ok.isna(),
         (e_ok == False) & (v_ok == False),   # noqa
         (e_ok == False),                      # noqa
         (v_ok == False)],                     # noqa
        ["no_summary", "fail_both", "fail_entries", "fail_value"],
        default="pass",
    )
    f["checksum_status"] = status

    r = f["value_ratio"]
    scale = ((r > 900) & (r < 1100)) | ((r > 0.0009) & (r < 0.0011))
    ed = f["entry_diff"].abs()
    cause = np.select(
        [
            f["checksum_status"] == "pass",
            f["checksum_status"] == "no_summary",
            f["n_rows"] == 0,
            (f["entry_total"] == 0) & (f["value_total"] == 0) & (f["n_rows"] <= 1),  # noqa
            (f["entry_total"] == 0) & (f["value_total"] == 0),                     # noqa
            (e_ok == False) & (f["entry_total"] == f["value_total"]),             # noqa
            scale,
            (e_ok == False) & ((f["entry_total"] - f["n_distinct_cusip"]).abs() <= 2),  # noqa
            (e_ok == False) & (ed <= 2) & (v_ok != False),                        # noqa
            (e_ok == False) & (ed <= 2) & (v_ok == False) & ((r - 1).abs() <= 0.01),  # noqa
            (e_ok == False) & (ed <= 2) & (v_ok == False),                        # noqa
            (e_ok == False),                                                       # noqa
            (v_ok == False) & ((r - 1).abs() <= 0.01),                             # noqa
            (v_ok == False),                                                       # noqa
        ],
        [
            "",
            "summary page missing",
            "no rows parsed",
            "empty filing (single placeholder row, totals zero)",
            "summary totals zero but holdings present (filer omitted totals)",
            "summary fields swapped (entry total = value total)",
            "value scale x1000 (dollars vs thousands)",
            "entry total counts distinct CUSIPs not rows",
            "entry count off by <=2",
            "entry off by <=2 and value within 1%",
            "entry off by <=2 and value off >1%",
            "entry count off by >2, unexplained",
            "value within 1% (rounding)",
            "value off >1%, unexplained",
        ],
        default="unclassified",
    )
    f["checksum_cause"] = cause
    return f
