from pathlib import Path

import pandas as pd

DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "comparable_bonds.csv"


def load_comparables() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE)
    for col in ("callable", "esg_label"):
        df[col] = df[col].astype(bool)
    return df
