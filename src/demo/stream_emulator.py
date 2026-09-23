"""Replay recorded samples by elapsed timestamp; no live race connection."""

import numpy as np
import pandas as pd


def advance_buffer(df_stream, idx: int, speed: float, step_sec: float):
    if speed <= 0 or step_sec <= 0 or idx < 0:
        raise ValueError("Replay speed and time step must be positive; index must be non-negative.")
    if "TimeSeconds" not in df_stream:
        raise ValueError("Replay requires TimeSeconds.")
    times = df_stream["TimeSeconds"].to_numpy()
    if not np.isfinite(times).all() or (np.diff(times) <= 0).any():
        raise ValueError("Replay timestamps must be finite and strictly increasing.")
    if idx >= len(df_stream):
        return df_stream.iloc[0:0].copy(), len(df_stream)
    target = times[idx] + speed * step_sec
    end = max(idx + 1, int(np.searchsorted(times, target, side="left")))
    end = min(end, len(df_stream))
    return df_stream.iloc[idx:end].copy(), end


def make_demo() -> pd.DataFrame:
    """Deterministic invented lap, with deliberate speed changes for testing.

    Not measured F1 telemetry. No third-party data is redistributed.
    """
    t = np.arange(0, 80, 0.2)
    speed = 215 + 55 * np.sin(t / 5)
    speed[105:111] -= np.arange(1, 7) * 15
    speed[111:119] -= np.linspace(90, 0, 8)
    speed[255:261] -= np.arange(1, 7) * 18
    speed[261:269] -= np.linspace(108, 0, 8)
    brake = (np.gradient(speed) < -1).astype(int)
    throttle = np.where(brake, 0, 85 + 15 * np.sin(t / 4))
    distance = np.cumsum(speed / 3.6 * 0.2)
    return pd.DataFrame(
        {
            "TimeSeconds": t,
            "Distance": distance - distance[0],
            "Speed": speed,
            "Throttle": throttle,
            "Brake": brake,
            "DRS": np.where(speed > 240, 12, 0),
            "RPM": 9000 + speed * 10,
            "nGear": np.clip((speed / 40).astype(int), 1, 8),
        }
    )
