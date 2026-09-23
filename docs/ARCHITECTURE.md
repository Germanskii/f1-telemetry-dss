# Architecture and portfolio changes

## Original academic implementation

The source archive contained a FastF1 loader, duplicate feature engineering routines,
a rule-based anomaly detector, a recommendations module, a large Streamlit dashboard,
a replay emulator and an intent-based assistant. The portfolio version keeps this
module-level organization and mathematical approach, with smaller explicit data flows.

A clean original startup without cached/processed data reproduced `KeyError: Distance`.
The earlier audit suspected divergent project roots; executing the original path
calculations showed they were the same. Centralized paths are a maintainability change,
not evidence that an original root mismatch existed.

## Changes made during preparation

- Replaced the initial no-data failure with a deterministic, clearly labelled synthetic demo.
- Consolidated preprocessing. Original speed differences were smoothed with a fixed window;
  acceleration omitted elapsed time, and smoothing also changed discrete channel values.
- Connected all analysis controls directly to the shared pipeline. The previous dashboard
  wrote environment variables that the detector did not read.
- Removed the unused detector smoothing argument. Smoothing now happens once in preprocessing.
- Retained IQR thresholds and 25 m / 12 m clustering. Removed the separate braking-mask bypass
  so both threshold controls consistently govern candidates. Numeric results are intentionally
  different from the thesis version and should not be compared as unchanged outputs.
- Eliminated duplicate cause classification and randomized advice. Counts include CHECK.
- Fixed zero-brake classification, non-default index handling and DRS-open interpretation.
- Reworded mechanical diagnoses as contextual review prompts; available channels do not
  establish tyre temperature, brake overheating or aerodynamic damage.
- Replaced stale file-based assistant reads with the active in-memory analysis.
- Replaced assumed replay sampling intervals with timestamp-based chunking.
- Rebuilt the interface in English while retaining lap selection, replay, plots, report
  exports and fixed-intent questions. Added CSV upload and the offline demo.
- Replaced optional Kaleido export with Plotly’s browser PNG download; HTML export embeds
  Plotly and can be opened without a network connection.
- Removed unused heavyweight direct dependencies such as PyTorch, FastAPI and scikit-learn.
  Added development checks and a GitHub Actions matrix.

## Deliberate differences from the archived UI

The assistant addresses the complete selected lap; replay has its own plot, intervals,
review prompts and CSV export. The old duplicate global/replay chat controls are consolidated.
Replay data is not silently autosaved to shared files. Session downloads occur on explicit
request rather than loading an event schedule during startup. The presets menu is replaced
by a reproducible demo and explicit event inputs. These are scope/UX changes, not just translation.

## Code reading order

1. `src/demo/stream_emulator.py`: where the demonstration data comes from.
2. `src/data_pipeline/preprocessing/feature_engineering.py`: units and validation.
3. `src/models/anomaly_detection.py`: threshold, clustering and hypothesis labels.
4. `src/models/recommendations.py`: stable intervals and review prompts.
5. `src/analysis.py`: composition, plotting, CLI and HTML export.
6. `src/dashboard/app.py`: input handling, session state and replay.
7. `src/agent/simple_agent.py`: limited intents; no generative AI runtime.

## Known limits

The thresholds are exploratory, not calibrated against confirmed faults. The synthetic
example deliberately contains sharp changes and validates software behavior, not diagnostic
quality. Sampling frequency affects speed-difference thresholds. Normal corners may be flagged.
Replay does not model a causal, production live detector. There is no comparison against a
reference lap, tyre model, race strategy optimizer or automated engineering action.
