"""Validate lap telemetry and derive physically labelled features."""

from pathlib import Path
import numpy as np
import pandas as pd
from src.paths import PROCESSED_DIR


def preprocess_telemetry(telemetry: pd.DataFrame, rolling_win: int = 5) -> pd.DataFrame:
    """Smooth speed only; retain discrete brake, gear and DRS channels.

    Speed_Diff is km/h per sample, not acceleration. Acceleration is m/s²
    when timestamps are available, otherwise unavailable (NaN).
    """
    if not isinstance(rolling_win, int) or not 1 <= rolling_win <= 101:
        raise ValueError("Smoothing window must be an integer between 1 and 101.")
    required = {"Distance", "Speed"}
    if not required.issubset(telemetry.columns):
        raise ValueError("Telemetry requires Distance (m) and Speed (km/h) columns.")
    if len(telemetry) < 2:
        raise ValueError("Telemetry must contain at least two samples.")
    channels = [
        c
        for c in ["Distance", "Speed", "RPM", "nGear", "Throttle", "Brake", "DRS"]
        if c in telemetry
    ]
    out = telemetry[channels].apply(pd.to_numeric, errors="raise").astype(float)
    if not np.isfinite(out.to_numpy()).all():
        raise ValueError("Telemetry channels must contain finite numeric values without gaps.")
    if (out["Speed"] < 0).any() or (out["Distance"].diff().dropna() < 0).any():
        raise ValueError("Speed must be non-negative and Distance must not decrease within a lap.")
    for col, maximum in [("Brake", 1), ("Throttle", 100)]:
        if col in out and not out[col].between(0, maximum).all():
            raise ValueError(f"{col} must be between 0 and {maximum}.")
    out = out.reset_index(drop=True)
    seconds = None
    if "TimeSeconds" in telemetry:
        seconds = pd.to_numeric(telemetry["TimeSeconds"], errors="raise").to_numpy(float)
    elif "Time" in telemetry:
        seconds = pd.to_timedelta(telemetry["Time"], errors="raise").dt.total_seconds().to_numpy()
    if seconds is not None:
        if not np.isfinite(seconds).all() or (np.diff(seconds) <= 0).any():
            raise ValueError("Time must contain finite, strictly increasing timestamps.")
        out["TimeSeconds"] = seconds - seconds[0]
    out["Speed_Smoothed"] = out["Speed"].rolling(rolling_win, center=True, min_periods=1).mean()
    out["Speed_Diff"] = out["Speed_Smoothed"].diff().fillna(0)
    out["Speed_mps"] = out["Speed"] / 3.6
    out["Acceleration"] = (
        out["Speed_mps"].diff() / out["TimeSeconds"].diff() if seconds is not None else np.nan
    )
    if seconds is not None:
        out.loc[0, "Acceleration"] = 0.0
    for col in ["Throttle", "Brake"]:
        if col in out:
            out[f"{col}_Diff"] = out[col].diff().fillna(0)
    for col in ["Speed", "Speed_Diff", "Throttle", "Brake", "RPM"]:
        if col in out:
            span = out[col].max() - out[col].min()
            out[f"{col}_Norm"] = (out[col] - out[col].min()) / span if span else 0.0
    return out


def save_processed_data(df: pd.DataFrame, output_path=None):
    path = Path(output_path) if output_path else PROCESSED_DIR / "telemetry_features.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return str(path)
