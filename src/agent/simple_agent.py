"""Small English intent router over the active result. No LLM or external service."""

import re
import pandas as pd
from src.models.anomaly_detection import summarize
from src.models.recommendations import build_segments, generate_recommendations


class F1SimpleAgent:
    def respond(self, question: str, context=None) -> str:
        df = (context or {}).get("data")
        if not isinstance(df, pd.DataFrame) or df.empty:
            return "No active analysis. Load a lap or the synthetic demo first."
        query = question.strip().lower()
        counts = summarize(df)
        if "compare" in query or "halves" in query:
            midpoint = (df["Distance"].min() + df["Distance"].max()) / 2
            parts = [df[df["Distance"] <= midpoint], df[df["Distance"] > midpoint]]
            return "Distance halves (descriptive, not a performance ranking):\n\n" + "\n".join(
                f"- {label}: {int(part['Anomaly'].sum())}/{len(part)} samples flagged."
                for label, part in zip(["First half", "Second half"], parts)
            )
        if "action" in query or "recommend" in query:
            return "\n".join(generate_recommendations(df)[0])
        causes = [c for c in ["BRAKES", "GRIP", "THROTTLE", "AERO", "CHECK"] if c.lower() in query]
        if "top" in query or "segment" in query or causes:
            segments = build_segments(df)
            if causes:
                segments = segments[segments["cause"].isin(causes)]
            match = re.search(r"top\s*(\d+)", query)
            n = min(20, max(1, int(match.group(1)))) if match else 5
            segments = segments.assign(length=segments["end_m"] - segments["start_m"])
            segments = segments.sort_values("length", ascending=False).head(n)
            lines = [
                f"- {r.start_m:.0f}-{r.end_m:.0f} m: {r.cause}, {r.points} samples."
                for r in segments.itertuples()
            ]
            return "\n".join(lines) if lines else "No matching flagged segments."
        if not any(word in query for word in ["summary", "tldr", "tl;dr"]):
            return "Supported questions: summary, top 3 segments, brakes, compare halves, actions."
        return (
            f"{counts['anomalies']} of {counts['rows']} samples flagged "
            f"({counts['rate']:.1f}%). Categories: {counts['causes'] or 'none'}. "
            "The flagged share is not model accuracy. Labels are review hypotheses."
        )
