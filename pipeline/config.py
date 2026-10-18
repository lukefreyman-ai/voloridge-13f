from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def load(path: Path | None = None) -> dict:
    p = path or ROOT / "config.yaml"
    with open(p) as f:
        cfg = yaml.safe_load(f)
    cfg["_root"] = ROOT
    cfg["edgar"]["cache_dir"] = ROOT / cfg["edgar"]["cache_dir"]
    cfg["output_dir"] = ROOT / cfg["output_dir"]
    import os   # env overrides so a background download and a foreground job can share the SEC rate budget (10 req/s total)
    if os.environ.get("EDGAR_RATE"):
        cfg["edgar"]["rate_limit_per_sec"] = float(os.environ["EDGAR_RATE"])
    if os.environ.get("EDGAR_WORKERS"):
        cfg["edgar"]["workers"] = int(os.environ["EDGAR_WORKERS"])
    return cfg
