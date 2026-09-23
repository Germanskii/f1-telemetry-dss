"""English Streamlit interface for the thesis telemetry analysis workflow."""

from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from src.analysis import analyze, figure, export_html_report
from src.agent.simple_agent import F1SimpleAgent
from src.demo.stream_emulator import make_demo, advance_buffer
from src.models.anomaly_detection import summarize
from src.models.recommendations import build_segments, generate_recommendations


def set_source(raw, label):
    # Validate before replacing the current valid lap.
    analyze(raw)
    st.session_state.raw = raw
    st.session_state.source_label = label
    st.session_state.replay_index = 2
    st.session_state.playing = False
    st.session_state.pop("answer", None)


def show_results(result, label, key):
    summary = summarize(result)
    a, b, c = st.columns(3)
    a.metric("Samples", summary["rows"])
    b.metric("Flagged samples", summary["anomalies"])
    c.metric("Flagged share", f"{summary['rate']:.1f}%")
    st.caption(
        "Flagged share is not model accuracy. Review labels are hypotheses, not fault diagnoses."
    )
    channels = [
        c
        for c in ["Speed", "Speed_Diff", "Throttle", "Brake", "RPM", "Acceleration"]
        if c in result and result[c].notna().any()
    ]
    channel = st.selectbox("Telemetry channel", channels, key=f"channel_{key}")
    st.plotly_chart(figure(result, channel), use_container_width=True, key=f"plot_{key}")
    st.caption(
        f"Source: {label} | Effective speed-change threshold: "
        f"{summary['thresholds']['abs_thr_used']:.2f} km/h per sample"
    )
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Flagged intervals")
        st.dataframe(build_segments(result), hide_index=True, width="stretch")
    with right:
        st.subheader("Review prompts")
        st.text("\n".join(generate_recommendations(result)[0]))


def main():
    st.set_page_config(page_title="F1 Telemetry DSS", page_icon="🏎️", layout="wide")
    st.title("F1 Telemetry · Decision Support")
    st.caption(
        "A Software Engineering thesis project by German Kashirski · Historical lap analysis"
    )
    if "raw" not in st.session_state:
        set_source(make_demo(), "Synthetic demonstration — not real F1 telemetry")
    with st.sidebar:
        st.header("Data source")
        if st.button("Load synthetic demo", width="stretch"):
            set_source(make_demo(), "Synthetic demonstration — not real F1 telemetry")
        source_mode = st.radio("Input mode", ["Demo / CSV", "FastF1 session"])
        if source_mode == "Demo / CSV":
            upload = st.file_uploader("Upload one-lap telemetry CSV", type=["csv"])
            if upload is not None and st.button("Analyze uploaded CSV"):
                try:
                    set_source(pd.read_csv(upload), f"Uploaded CSV: {upload.name}")
                except (ValueError, TypeError, pd.errors.ParserError) as exc:
                    st.error(str(exc))
        else:
            st.caption(
                "Downloads historical data. Cache-only mode needs an earlier successful download."
            )
            with st.form("session_form"):
                year = st.number_input("Year", 2018, 2030, 2023)
                event = st.text_input("Grand Prix", "Italian Grand Prix")
                kind = st.selectbox("Session", ["Q", "R", "FP1", "FP2", "FP3", "S", "SQ"])
                offline = st.checkbox("Cache only")
                submit = st.form_submit_button("Load session")
            if submit:
                try:
                    from src.data_pipeline.load_fastf1_data import load_f1_session

                    with st.spinner("Loading session…"):
                        session = load_f1_session(int(year), event, kind, offline)
                    st.session_state.session = session
                    st.session_state.session_label = f"{year} {event} / {kind}"
                except Exception as exc:
                    st.error(str(exc))
            if "session" in st.session_state:
                session = st.session_state.session
                st.caption("Loaded: " + st.session_state.session_label)
                drivers = sorted(session.laps["Driver"].dropna().unique().tolist())
                driver = st.selectbox("Driver", drivers)
                laps = session.laps.pick_drivers(driver)
                options = ["Fastest"] + [str(int(n)) for n in laps["LapNumber"].dropna().unique()]
                lap_id = st.selectbox("Lap", options)
                if st.button("Analyze selected lap"):
                    try:
                        lap = (
                            laps.pick_fastest()
                            if lap_id == "Fastest"
                            else laps[laps["LapNumber"] == int(lap_id)].iloc[0]
                        )
                        if lap is None:
                            raise ValueError("No timed lap available for this driver.")
                        raw = lap.get_car_data().add_distance().reset_index(drop=True)
                        set_source(
                            raw,
                            f"{st.session_state.session_label} / {driver} / lap {int(lap['LapNumber'])}",
                        )
                    except Exception as exc:
                        st.error(f"Could not analyze the lap: {exc}")
        st.divider()
        st.header("Analysis settings")
        iqr = st.slider("IQR multiplier", 0.0, 5.0, 1.5, 0.1)
        minimum = st.slider("Minimum speed change (km/h per sample)", 1.0, 40.0, 8.0, 0.5)
        window = st.slider("Smoothing window (samples)", 1, 21, 5, 2)
        st.caption(
            "Settings apply immediately to the selected raw lap. Larger windows smooth more strongly."
        )
    result = analyze(st.session_state.raw, iqr, minimum, window)
    label = st.session_state.source_label
    st.info(label)
    analysis_tab, replay_tab, assistant_tab = st.tabs(
        ["Lap analysis", "Historical replay", "Rule-based assistant"]
    )
    with analysis_tab:
        show_results(result, label, "lap")
        st.subheader("Export analysis")
        a, b, c = st.columns(3)
        a.download_button(
            "Download CSV", result.to_csv(index=False), "telemetry_analysis.csv", "text/csv"
        )
        b.download_button(
            "Download summary",
            json.dumps(summarize(result), indent=2),
            "summary.json",
            "application/json",
        )
        c.download_button(
            "Download HTML report",
            export_html_report(result, label),
            "telemetry_report.html",
            "text/html",
        )
        st.caption(
            "The HTML report includes the chart and works offline. The plot toolbar also offers PNG export."
        )
    with replay_tab:
        st.caption(
            "Replay of the selected recorded lap; not live race telemetry. "
            "Each prefix is re-analyzed, so earlier flags may change as samples arrive."
        )
        if "TimeSeconds" not in result:
            st.warning(
                "Replay needs TimeSeconds (seconds) or Time (timedelta). Upload timestamped data."
            )
        else:
            speed = st.slider("Playback speed", 1, 20, 4)
            a, b, c = st.columns(3)
            if a.button("Start / resume"):
                st.session_state.playing = True
            if b.button("Pause"):
                st.session_state.playing = False
            if c.button("Reset replay"):
                st.session_state.replay_index = 2
                st.session_state.playing = False

            @st.fragment(run_every=0.5 if st.session_state.playing else None)
            def replay():
                index = st.session_state.replay_index
                if st.session_state.playing:
                    _, index = advance_buffer(result, index, speed, 0.5)
                    st.session_state.replay_index = index
                    if index >= len(result):
                        st.session_state.playing = False
                        st.rerun()
                prefix = analyze(st.session_state.raw.iloc[: max(2, index)], iqr, minimum, window)
                st.progress(
                    min(index / len(result), 1.0), text=f"Replayed {index} / {len(result)} samples"
                )
                show_results(prefix, label + " (replay prefix)", "replay")
                st.download_button(
                    "Download replay CSV", prefix.to_csv(index=False), "replay.csv", "text/csv"
                )

            replay()
    with assistant_tab:
        st.write(
            "Ask about the complete selected lap. This assistant uses fixed intents, not an LLM."
        )
        st.caption("Try: summary · top 3 segments · brakes · compare halves · actions")
        question = st.text_input("Question", "summary")
        if st.button("Ask assistant"):
            st.session_state.answer = F1SimpleAgent().respond(question, {"data": result})
            st.session_state.answer_settings = (label, iqr, minimum, window)
        if (
            st.session_state.get("answer_settings") == (label, iqr, minimum, window)
            and "answer" in st.session_state
        ):
            st.markdown(st.session_state.answer)
    st.caption("Independent academic project. Not affiliated with Formula 1, teams or FastF1.")


if __name__ == "__main__":
    main()
