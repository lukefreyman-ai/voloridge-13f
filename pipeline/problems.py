"""Collect data problems; write PROBLEMS.md + problems.csv. No silent failures."""
from pathlib import Path
import pandas as pd


class Problems:
    def __init__(self):
        self.rows = []

    def add(self, stage: str, accession: str, reason: str, detail: str = ""):
        self.rows.append({"stage": stage, "accession": accession, "reason": reason, "detail": detail})

    def df(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["stage", "accession", "reason", "detail"])

    def write(self, out_dir: Path, title: str):
        out_dir.mkdir(parents=True, exist_ok=True)
        df = self.df()
        df.to_csv(out_dir / "problems.csv", index=False)
        md = [f"# PROBLEMS — {title}", "", f"Total logged: {len(df)}", ""]
        if len(df):
            md.append("## By stage / reason")
            md.append("")
            md.append(df.groupby(["stage", "reason"]).size().sort_values(ascending=False).to_string())
            md.append("")
            md.append("## First 200 entries")
            md.append("")
            md.append(df.head(200).to_markdown(index=False))
        (out_dir / "PROBLEMS.md").write_text("\n".join(md))
