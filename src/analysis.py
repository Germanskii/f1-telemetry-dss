"""Shared analysis and export entry points, independent of Streamlit."""

import argparse
import html
import json
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from src.data_pipeline.preprocessing.feature_engineering import preprocess_telemetry
from src.models.anomaly_detection import detect_anomalies, summarize, save_outputs
from src.models.recommendations import generate_recommendations
from src.demo.stream_emulator import make_demo
from src.paths import RESULTS_DIR


def analyze(telemetry, iqr_k=1.5, min_speed_diff=8.0, rolling_win=5):
    features = preprocess_telemetry(telemetry, rolling_win)
    result = detect_anomalies(features, iqr_k, min_speed_diff)
    result.attrs["thresholds"]["rolling_win"] = rolling_win
    return result


def figure(df, channel="Speed"):
    fig = go.Figure()
    fig.add_scatter(
        x=df["Distance"],
        y=df[channel],
        name=channel,
        mode="lines",
        line={"color": "#60a5fa", "width": 2},
    )
    for cause, group in df[df["Anomaly"]].groupby("CAUSE"):
        fig.add_scatter(x=group["Distance"], y=group[channel], name=cause, mode="markers")
    unit = {
        "Speed": "km/h",
        "Speed_Smoothed": "km/h",
        "Throttle": "%",
        "Brake": "0/1",
        "Acceleration": "m/s²",
        "RPM": "rpm",
        "Speed_Diff": "km/h per sample",
    }.get(channel, "")
    fig.update_layout(
        template="plotly_dark",
        height=420,
        xaxis_title="Lap distance (m)",
        yaxis_title=f"{channel} ({unit})",
        margin=dict(l=20, r=20, t=25, b=20),
        legend=dict(orientation="h", y=1.1),
    )
    return fig


def export_html_report(df, source="Unknown source"):
    lines, _ = generate_recommendations(df)
    chart = figure(df).to_html(full_html=False, include_plotlyjs=True)
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<title>F1 Telemetry Review</title><body><h1>F1 Telemetry Review</h1>"
        f"<p>{html.escape(source)}</p><p>Academic heuristic analysis; not a diagnosis.</p>"
        + chart
        + "<h2>Summary and settings</h2><pre>"
        + html.escape(json.dumps(summarize(df), indent=2))
        + "</pre><h2>Review prompts</h2><pre>"
        + html.escape("\n".join(lines))
        + "</pre></body></html>"
    )


def main():
    parser = argparse.ArgumentParser(description="Analyze a synthetic demo or one-lap CSV.")
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--output", type=Path, default=RESULTS_DIR)
    args = parser.parse_args()
    raw = pd.read_csv(args.csv) if args.csv else make_demo()
    source = args.csv.name if args.csv else "Synthetic demonstration (not real F1 data)"
    result = analyze(raw)
    args.output.mkdir(parents=True, exist_ok=True)
    save_outputs(result, args.output / "telemetry.csv", args.output / "summary.json")
    (args.output / "report.html").write_text(export_html_report(result, source), encoding="utf-8")
    lines, _ = generate_recommendations(result)
    (args.output / "recommendations.txt").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summarize(result), indent=2))


if __name__ == "__main__":
    main()
