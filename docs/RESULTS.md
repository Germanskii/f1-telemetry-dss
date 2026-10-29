# Reproducing and interpreting the results

Observed on 29 October 2026 using the existing Windows / Python 3.10.11 project
environment. These are software and integration results, not a fault-detection benchmark.
Run commands from the repository root after installing the README dependencies.

## Offline demonstration

```bash
python -m src.analysis --output results/demo
```

Expected summary: **400 rows**, **28 flagged samples**, **7.0% flagged share**,
**12 BRAKES / 16 CHECK**. Settings: IQR multiplier **1.5**, minimum speed change
**8 km/h per sample**, smoothing window **5 samples**; effective threshold **8**.
The unrounded JSON is included in [examples/demo-summary.json](examples/demo-summary.json).

The output directory contains:

| File | Contents |
| --- | --- |
| `telemetry.csv` | Validated channels, derived features, flag mask and heuristic labels |
| `summary.json` | Row / flag counts, flagged percentage, category counts and settings |
| `recommendations.txt` | Deterministic prompts for reviewing flagged intervals |
| `report.html` | Interactive Plotly chart, summary and prompts; Plotly is embedded |

Open `results/demo/report.html` in a browser. Results are ignored by Git; this
repository includes only the small synthetic JSON example and dashboard screenshot.

## Sensitivity to a review setting

```bash
python -c "from src.analysis import analyze; from src.demo.stream_emulator import make_demo; from src.models.anomaly_detection import summarize; print(summarize(analyze(make_demo(), min_speed_diff=40)))"
```

Expected: **400 rows**, **0 flags**, effective threshold **40**. All other settings
are unchanged. This checks that the parameter affects the result. It does not
establish which setting is best for real telemetry.

## Historical integration

After downloading **2023 / Italian Grand Prix / Q** through the dashboard, this
command uses the local cache without requesting a fresh download:

```bash
python -c "from src.data_pipeline.load_fastf1_data import load_f1_session, get_fastest_lap_telemetry; from src.analysis import analyze; from src.models.anomaly_detection import summarize; s = load_f1_session(2023, 'Italian Grand Prix', 'Q', force_offline=True); print(summarize(analyze(get_fastest_lap_telemetry(s))))"
```

Observed session-fastest lap: **SAI, lap 19**. Result: **296 rows**, **27 flags**,
**9.12% flagged share**, **22 BRAKES / 3 CHECK / 2 THROTTLE**, effective threshold
approximately **14.225 km/h per sample**, with default analysis settings.
Cache-only mode fails if the necessary session data has not been downloaded.
Historical results depend on upstream data and library versions; raw telemetry
and cache files are not redistributed here.

## What the numbers mean

- `rows` counts telemetry samples in one lap, not laps, races or users.
- `anomalies` counts samples retained after distance clustering; it is not the
  number of separate incidents. Clusters can include intervening samples.
- `rate` is `100 × flagged samples / all samples`. The JSON floating-point value
  `7.000000000000001` is displayed as **7.0%** in the dashboard.
- `causes` contains rule-derived review categories. A BRAKES label does not
  demonstrate a brake fault; the input has no confirmed mechanical-fault labels.
- Passing 14 tests establishes behavior in the exercised cases. It does not
  measure model accuracy, speedup, time saved, reliability at scale or user impact.

The detector uses sample-to-sample changes in smoothed speed. These depend on
sampling density; acceleration is a separate elapsed-time feature. Centred
smoothing and prefix-wide IQR calculations make replay retrospective.

## Evidence boundaries

The [validation record](VALIDATION.md) separates the October recheck from the
September browser checks. Current tests run offline, including Streamlit AppTest;
the earlier full-browser checks are not an automated browser suite in CI.
There is no labelled holdout set, precision / recall estimate, trained model,
live race feed or production deployment. Evaluating a learned detector would
require a defined target, independent labels and a leakage-aware split before
claiming an improvement over this heuristic baseline.
