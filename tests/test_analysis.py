import json
import numpy as np
import pandas as pd
import pytest
from src.analysis import analyze, export_html_report
from src.demo.stream_emulator import make_demo, advance_buffer
from src.data_pipeline.preprocessing.feature_engineering import preprocess_telemetry
from src.models.anomaly_detection import detect_anomalies, save_outputs, summarize, _assign_cause
from src.models.recommendations import generate_recommendations, build_segments
from src.agent.simple_agent import F1SimpleAgent


def test_demo_and_exports(tmp_path):
    result = analyze(make_demo())
    assert len(result) == 400
    assert 0 < result["Anomaly"].sum() < len(result)
    lines, counts = generate_recommendations(result)
    assert counts == summarize(result)["causes"]
    assert sum(counts.values()) == int(result["Anomaly"].sum())
    assert generate_recommendations(result)[0] == lines
    save_outputs(result, tmp_path / "out.csv", tmp_path / "summary.json")
    restored = pd.read_csv(tmp_path / "out.csv")
    assert restored["CAUSE"].fillna("").equals(result["CAUSE"])
    assert (
        json.loads((tmp_path / "summary.json").read_text())["anomalies"] == result["Anomaly"].sum()
    )
    report = export_html_report(result, "<script>alert(1)</script>")
    assert "&lt;script&gt;" in report and "<script>alert(1)" not in report
    assert "plotly.js" in report


def test_controls_change_actual_analysis():
    raw = make_demo()
    normal = analyze(raw, rolling_win=1)
    smooth = analyze(raw, rolling_win=21)
    assert not normal["Speed_Diff"].equals(smooth["Speed_Diff"])
    assert normal["Anomaly"].sum() != smooth["Anomaly"].sum()
    assert analyze(raw, min_speed_diff=40)["Anomaly"].sum() == 0
    assert (
        analyze(raw, min_speed_diff=1, iqr_k=0).attrs["thresholds"]["abs_thr_used"]
        < analyze(raw, min_speed_diff=1, iqr_k=5).attrs["thresholds"]["abs_thr_used"]
    )


def test_acceleration_uses_elapsed_seconds_and_discrete_channels_survive():
    raw = pd.DataFrame(
        {
            "Distance": [0, 10, 30],
            "Speed": [0, 36, 72],
            "TimeSeconds": [0, 2, 6],
            "Brake": [False, True, False],
            "DRS": [0, 12, 0],
        }
    )
    result = preprocess_telemetry(raw, 3)
    np.testing.assert_allclose(result["Acceleration"], [0, 5, 2.5])
    assert result["DRS"].tolist() == [0, 12, 0]
    assert result["Brake"].tolist() == [0, 1, 0]
    assert preprocess_telemetry(raw.drop(columns="TimeSeconds"))["Acceleration"].isna().all()


@pytest.mark.parametrize("mutation", ["missing", "nan", "time", "distance", "brake", "short"])
def test_invalid_data_is_rejected(mutation):
    raw = make_demo()
    if mutation == "missing":
        raw = raw.drop(columns="Speed")
    elif mutation == "nan":
        raw.loc[5, "Speed"] = np.nan
    elif mutation == "time":
        raw.loc[5, "TimeSeconds"] = raw.loc[4, "TimeSeconds"]
    elif mutation == "distance":
        raw.loc[5, "Distance"] = -100
    elif mutation == "brake":
        raw.loc[5, "Brake"] = 100
    else:
        raw = raw.iloc[:1]
    with pytest.raises(ValueError):
        analyze(raw)


def test_replay_uses_irregular_timestamps_and_finishes():
    raw = pd.DataFrame({"TimeSeconds": [0, 0.1, 0.9, 2, 4]})
    chunk, index = advance_buffer(raw, 0, 1, 1)
    assert index == 3 and len(chunk) == 3
    _, index = advance_buffer(raw, index, 10, 1)
    assert index == len(raw)
    assert advance_buffer(raw, index, 1, 1)[0].empty


def test_brake_zero_not_classified_as_braking_and_drs_codes():
    assert _assign_cause({"Speed_Diff": -12, "Brake": 0, "DRS": 0}, 8) == "GRIP"
    assert _assign_cause({"Speed_Diff": -12, "Brake": 0, "DRS": 12}, 8) == "AERO"
    assert _assign_cause({"Speed_Diff": -12, "Brake": 0, "DRS": 1}, 8) != "AERO"


def test_nondefault_index_and_check_counts():
    features = preprocess_telemetry(make_demo())
    features.index = np.arange(len(features)) + 100
    result = detect_anomalies(features)
    assert len(result) == len(features)
    assert "CHECK" in summarize(result)["causes"]
    assert build_segments(result)["points"].sum() == result["Anomaly"].sum()


def test_assistant_uses_supplied_analysis():
    agent = F1SimpleAgent()
    result = analyze(make_demo())
    assert "28 of 400" in agent.respond("summary", {"data": result})
    assert "BRAKES" in agent.respond("brakes", {"data": result})
    assert "First half" in agent.respond("compare halves", {"data": result})
    assert "review" in agent.respond("actions", {"data": result}).lower()
    assert "Supported questions" in agent.respond("predict the winner", {"data": result})
    assert "No active analysis" in agent.respond("summary")
