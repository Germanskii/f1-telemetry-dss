"""Optional historical telemetry acquisition through FastF1."""

from src.paths import CACHE_DIR
from src.data_pipeline.preprocessing.feature_engineering import (
    preprocess_telemetry as preprocess_telemetry_inline,
    save_processed_data,
)


def load_f1_session(year: int, grand_prix: str, session_type: str, force_offline=False):
    import fastf1

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))
    fastf1.Cache.offline_mode(bool(force_offline))
    try:
        session = fastf1.get_session(year, grand_prix, session_type)
        session.load(telemetry=True, laps=True, weather=False, messages=False)
        if session.laps.empty:
            raise ValueError("No laps available for this session.")
        return session
    except Exception as exc:
        raise RuntimeError(
            "Could not load the historical session. Check the event, network and cache. "
            "Cache-only mode requires a previously downloaded session."
        ) from exc
    finally:
        fastf1.Cache.offline_mode(False)


def get_fastest_lap_telemetry(session):
    lap = session.laps.pick_fastest()
    if lap is None:
        raise ValueError("No timed lap available.")
    return lap.get_car_data().add_distance().reset_index(drop=True)


def run_full_pipeline(year: int, gp: str, kind: str):
    telemetry = get_fastest_lap_telemetry(load_f1_session(year, gp, kind))
    features = preprocess_telemetry_inline(telemetry)
    save_processed_data(features)
    return telemetry, features
