"""Deterministic review prompts based on the detector's existing labels."""

import pandas as pd
from src.paths import PROCESSED_DIR, RESULTS_DIR
from src.models.anomaly_detection import summarize

TEXT_TEMPLATES = {
    "BRAKES": "Review this braking phase against a reference lap. A speed drop does not prove a brake fault.",
    "GRIP": "Review speed loss without braking. Corner geometry, lifting and traffic are alternative explanations.",
    "THROTTLE": "Compare throttle application and speed changes with a reference lap.",
    "AERO": "Review speed changes while DRS is open. These channels cannot establish an aerodynamic fault.",
    "CHECK": "Inspect the surrounding telemetry and context before interpreting this interval.",
}


def build_segments(df):
    """Split on label changes, normal samples and distance gaps over 25 m."""
    columns = ["start_m", "end_m", "points", "cause", "min_speed"]
    if df.empty or not df["Anomaly"].any():
        return pd.DataFrame(columns=columns)
    change = (
        df["CAUSE"].ne(df["CAUSE"].shift())
        | df["Anomaly"].ne(df["Anomaly"].shift())
        | df["Distance"].diff().gt(25)
    )
    groups = change.cumsum()
    rows = []
    for _, group in df[df["Anomaly"]].groupby(groups):
        rows.append(
            {
                "start_m": float(group["Distance"].iloc[0]),
                "end_m": float(group["Distance"].iloc[-1]),
                "points": len(group),
                "cause": group["CAUSE"].iloc[0],
                "min_speed": float(group["Speed"].min()) if "Speed" in group else None,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def generate_recommendations(df):
    if not {"Anomaly", "CAUSE", "Distance"}.issubset(df):
        raise ValueError("Run detection before generating review prompts.")
    counts = summarize(df)["causes"]
    if not df["Anomaly"].any():
        return [
            "No samples flagged at these settings. This does not establish fault-free operation."
        ], counts
    lines = ["Telemetry review prompts (heuristic; not mechanical diagnoses)"]
    for row in build_segments(df).itertuples():
        lines.append(
            f"- [{row.start_m:.0f}-{row.end_m:.0f} m] [{row.cause}] "
            + TEXT_TEMPLATES.get(row.cause, TEXT_TEMPLATES["CHECK"])
        )
    return lines, counts


def main():
    df = pd.read_csv(PROCESSED_DIR / "telemetry_with_anomalies.csv")
    lines, _ = generate_recommendations(df)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "recommendations.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
