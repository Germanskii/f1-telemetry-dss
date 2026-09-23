"""IQR and speed-change heuristics; labels are review categories, not diagnoses."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.paths import PROCESSED_DIR, RESULTS_DIR


def _cluster_mask_by_distance(df, point_mask, ref_dist=25.0, min_len_m=12.0):
    indices = np.flatnonzero(point_mask)
    keep = np.zeros(len(df), dtype=bool)
    if not len(indices):
        return keep
    distance = df["Distance"].to_numpy()
    start = previous = indices[0]
    for current in indices[1:]:
        if distance[current] - distance[previous] > ref_dist:
            if distance[previous] - distance[start] >= min_len_m:
                keep[start : previous + 1] = True
            start = current
        previous = current
    if distance[previous] - distance[start] >= min_len_m:
        keep[start : previous + 1] = True
    return keep


def _assign_cause(row, min_speed_diff):
    change = row["Speed_Diff"]
    brake = row.get("Brake", np.nan)
    if brake >= 0.5 and change <= -min_speed_diff:
        return "BRAKES"
    if abs(row.get("Throttle_Diff", 0)) >= 3 and change >= min_speed_diff:
        return "THROTTLE"
    # FastF1 DRS codes 10, 12 and 14 mean open; 0/1/2/3 are not open.
    if row.get("DRS", 0) in (10, 12, 14) and abs(change) >= min_speed_diff:
        return "AERO"
    if brake < 0.5 and change <= -min_speed_diff:
        return "GRIP"
    return "CHECK"


def detect_anomalies(df, IQR_k=1.5, min_speed_diff=8.0):
    """Flag distance clusters of large sample-to-sample speed changes.

    Run feature engineering again to change smoothing; detection never applies
    a second smoothing pass. Filled cluster gaps can receive CHECK labels.
    """
    if not np.isfinite([IQR_k, min_speed_diff]).all() or IQR_k < 0 or min_speed_diff <= 0:
        raise ValueError("IQR multiplier must be non-negative; minimum change must be positive.")
    if not {"Speed_Diff", "Distance"}.issubset(df):
        raise ValueError("Detection requires Speed_Diff and Distance.")
    out = df.copy().reset_index(drop=True)
    if out.empty or not np.isfinite(out[["Speed_Diff", "Distance"]].to_numpy()).all():
        raise ValueError("Detection requires nonempty, finite features.")
    if (out["Distance"].diff().dropna() < 0).any():
        raise ValueError("Distance must not decrease within a lap.")
    magnitude = out["Speed_Diff"].abs()
    q1, q3 = magnitude.quantile([0.25, 0.75])
    threshold = max(min_speed_diff, float(q3 + IQR_k * max(q3 - q1, 1e-6)))
    out["Anomaly"] = _cluster_mask_by_distance(out, magnitude.ge(threshold).to_numpy())
    out["CAUSE"] = ""
    for index, row in out[out["Anomaly"]].iterrows():
        out.at[index, "CAUSE"] = _assign_cause(row, min_speed_diff)
    out.attrs["thresholds"] = {
        "IQR_k": float(IQR_k),
        "min_speed_diff": float(min_speed_diff),
        "abs_thr_used": float(threshold),
    }
    return out


def summarize(df):
    counts = df.loc[df["Anomaly"], "CAUSE"].value_counts().to_dict()
    return {
        "rows": len(df),
        "anomalies": int(df["Anomaly"].sum()),
        "rate": float(df["Anomaly"].mean() * 100),
        "causes": {str(k): int(v) for k, v in counts.items()},
        "thresholds": df.attrs.get("thresholds", {}),
    }


def save_outputs(df, out_csv=None, summary_json=None):
    csv = Path(out_csv) if out_csv else PROCESSED_DIR / "telemetry_with_anomalies.csv"
    summary = Path(summary_json) if summary_json else RESULTS_DIR / "summary.json"
    csv.parent.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv, index=False)
    summary.write_text(json.dumps(summarize(df), indent=2), encoding="utf-8")


def main(IQR_k=1.5, min_speed_diff=8.0, features_path=None, out_csv=None, summary_json=None):
    features = pd.read_csv(features_path or PROCESSED_DIR / "telemetry_features.csv")
    result = detect_anomalies(features, IQR_k, min_speed_diff)
    save_outputs(result, out_csv, summary_json)


if __name__ == "__main__":
    main()
