"""Apply local duration estimates to a copy and compare schedule outcomes."""
import pandas as pd

from ai_predictor import PROCESS, predict_hours


OUTCOME_COLUMNS = [
    "Job", "Component", "Due at", "Original finish", "AI finish",
    "Original delay (h)", "AI delay (h)", "Finish shift (h)", "Newly late",
]


def jobs_with_ai_durations(jobs):
    """Keep stored estimates, setup, deadlines and assignments untouched."""
    result = jobs.copy(deep=True)
    result[PROCESS] = predict_hours(jobs)
    return result


def compare_schedule_outcomes(original_plan, ai_plan, base_time):
    """Join by job ID, comparing the same sequencing policy and time origin."""
    if original_plan.empty and ai_plan.empty:
        return pd.DataFrame(columns=OUTCOME_COLUMNS)
    if original_plan.empty or ai_plan.empty:
        raise ValueError("Both schedules must contain the same jobs")
    if set(original_plan["Job"]) != set(ai_plan["Job"]):
        raise ValueError("Both schedules must contain the same jobs")

    original = original_plan[["Job", "Component", "Bitiş", "Teslim (saat)"]].rename(
        columns={"Bitiş": "Original finish"})
    estimated = ai_plan[["Job", "Bitiş"]].rename(columns={"Bitiş": "AI finish"})
    result = original.merge(estimated, on="Job", validate="one_to_one")
    result["Due at"] = pd.Timestamp(base_time) + pd.to_timedelta(result["Teslim (saat)"], unit="h")
    for source in ("Original", "AI"):
        result[f"{source} delay (h)"] = (
            (result[f"{source} finish"] - result["Due at"]).dt.total_seconds() / 3600
        ).clip(lower=0)
    result["Finish shift (h)"] = (
        result["AI finish"] - result["Original finish"]
    ).dt.total_seconds() / 3600
    result["Newly late"] = (result["Original delay (h)"] == 0) & (result["AI delay (h)"] > 0)
    return result[OUTCOME_COLUMNS]
