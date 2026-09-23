# Validation record

Local validation on **2026-09-23**, Windows, Python 3.10.11, dependencies from
`requirements.txt`. Dependencies were installed into a fresh project virtual environment.

## Reproduced baseline

- The previously installed system FastF1 failed to import because `exceptiongroup` was missing.
- In the isolated environment, the original archived dashboard failed on a clean start
  without processed CSV data: `KeyError: Distance`.
- Original path expressions were executed and resolved to the same project root, correcting
  the earlier static-audit suspicion. No original archive was modified.

## Automated local checks

- `python -m pip check`: no broken requirements.
- `python -m ruff check src tests`: passed.
- `python -m ruff format --check src tests`: passed.
- `python -m pytest -q`: **14 passed**.
- `python -m src.analysis`: completed, writing CSV, JSON, text and HTML output.

Tests cover input rejection, elapsed-time acceleration, preservation of discrete channels,
actual effects of smoothing and thresholds, non-default indices, consistent CHECK counts,
deterministic recommendations, DRS codes, irregular timestamp replay, report escaping,
assistant scope and Streamlit controls. They do not establish diagnostic accuracy.

## Synthetic demonstration

Default settings: IQR multiplier 1.5, minimum change 8 km/h per sample, smoothing window 5.
Observed 400 samples, 28 flagged (7.0%), including 12 BRAKES and 16 CHECK labels.
Raising the minimum speed change to 40 yielded zero flags. These are invented test data,
not measured F1 results or labelled fault examples.

## Historical telemetry integration

FastF1 successfully downloaded the **2023 Italian Grand Prix qualifying session**.
The session's overall fastest lap produced 296 samples and 27 flags with default settings
(22 BRAKES, 3 CHECK, 2 THROTTLE; effective threshold about 14.225 km/h per sample).

The browser UI then loaded this session in **cache-only mode**, selected **ALB, lap 20**,
and completed analysis with an effective threshold about 15.65 km/h per sample.
Downloaded data and caches are excluded from the repository. Other events and sessions
have not all been tested, and upstream availability is outside this application's control.

## Browser checks

Headless Microsoft Edge through Playwright against a real local Streamlit server:

- Synthetic demo plot rendered; English interface screenshot inspected.
- HTML report downloaded; its embedded chart rendered with HTTP/HTTPS requests blocked.
- Replay started, advanced, paused and reset to the initial two samples.
- Assistant answered a summary from the active analysis.
- Invalid CSV was rejected without crashing the app.
- Real driver/lap selection worked using the downloaded session cache.
- No page errors or Streamlit exception elements in the exercised demo workflow.

Browser checks were manual automation during preparation; they are not part of the
committed pytest suite. CI exercises offline tests and CLI on Linux/Python 3.10 and 3.12.
Its actual run status is visible in the repository's Actions tab.

## Remaining limits

No exhaustive cross-browser testing, load testing or labelled fault evaluation. No live
race connection, trained model, authenticated multi-user deployment or real engineering
validation. Windows Python 3.10 is the locally exercised environment. Do not interpret
successful software checks as proof of mechanical diagnosis or racing performance.
