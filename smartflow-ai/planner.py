"""Rule-based production planning helpers, independent from the Streamlit UI."""
from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Mapping, Sequence

import pandas as pd

MACHINES = {
    "Lathe-01": ["Torna"],
    "Machining-Center-01": ["Freze", "Delik"],
    "Assembly-Kitting-01": ["Montaj", "Paketleme"],
}


def build_plan(
    jobs: pd.DataFrame,
    machines: Mapping[str, Sequence[str]] = MACHINES,
    optimized: bool = False,
    base_time: datetime | None = None,
) -> pd.DataFrame:
    """Assign every job to a capable machine, respecting material readiness.

    Setup and processing occupy the machine consecutively. The baseline follows
    input order; the heuristic prioritizes high-priority, early-due jobs.
    """
    process_col = "S\u00fcre (saat)"
    setup_col = "Haz\u0131rl\u0131k (saat)"
    priority_col = "\u00d6ncelik"
    due_col = "Teslim (saat)"
    ready_col = "Malzeme (saat)"
    due_at_col = "Due at"
    ready_at_col = "Material ready at"
    required = {"Job", "Operasyon", process_col, setup_col, priority_col}
    missing = required.difference(jobs.columns)
    if missing:
        raise ValueError(f"Eksik Job alanlar\u0131: {', '.join(sorted(missing))}")
    has_absolute_times = due_at_col in jobs.columns and ready_at_col in jobs.columns
    has_legacy_offsets = due_col in jobs.columns and ready_col in jobs.columns
    if not has_absolute_times and not has_legacy_offsets:
        raise ValueError("Teslim ve malzeme haz\u0131r tarih/saatleri gerekli.")

    job_ids = jobs["Job"].astype("string").str.strip()
    if job_ids.isna().any() or job_ids.eq("").any():
        raise ValueError("Job ID bo\u015f olamaz.")
    if job_ids.str.casefold().duplicated().any():
        raise ValueError("Job ID de\u011ferleri benzersiz olmal\u0131d\u0131r.")

    numeric_columns = [process_col, setup_col, priority_col]
    if has_legacy_offsets and not has_absolute_times:
        numeric_columns.extend([due_col, ready_col])
    numeric = jobs[numeric_columns].apply(pd.to_numeric, errors="coerce")
    finite = numeric.apply(lambda column: column.map(lambda value: math.isfinite(float(value)))).all().all()
    if numeric.isna().any().any() or not finite:
        raise ValueError("Say\u0131sal alanlar ge\u00e7erli ve sonlu de\u011ferler olmal\u0131d\u0131r.")
    if (numeric[[process_col, setup_col]] < 0).any().any():
        raise ValueError("S\u00fcreler negatif olamaz.")
    if ((numeric[priority_col] < 1) | (numeric[priority_col] > 5) | (numeric[priority_col] % 1 != 0)).any():
        raise ValueError("\u00d6ncelik 1 ile 5 aras\u0131nda tam say\u0131 olmal\u0131d\u0131r.")

    base_time = base_time or datetime.now().replace(minute=0, second=0, microsecond=0)
    if has_absolute_times:
        due_dates = pd.to_datetime(jobs[due_at_col], errors="coerce")
        ready_dates = pd.to_datetime(jobs[ready_at_col], errors="coerce")
        if due_dates.isna().any() or ready_dates.isna().any():
            raise ValueError("Teslim ve malzeme haz\u0131r tarih/saatleri ge\u00e7erli olmal\u0131d\u0131r.")
        base_timestamp = pd.Timestamp(base_time)
        due_hours = (due_dates - base_timestamp).dt.total_seconds() / 3600
        ready_hours = (ready_dates - base_timestamp).dt.total_seconds() / 3600
        if (ready_dates > due_dates).any():
            raise ValueError("Malzeme hazir olma tarihi teslim tarihinden sonra olamaz.")
    else:
        due_hours = numeric[due_col].astype(float)
        ready_hours = numeric[ready_col].astype(float)
        if (ready_hours < 0).any():
            raise ValueError("Malzeme haz\u0131r zaman\u0131 negatif olamaz.")
        if (ready_hours > due_hours).any():
            raise ValueError("Malzeme hazir olma zamani teslim zamanindan sonra olamaz.")

    data = jobs.copy().reset_index(drop=True)
    data["Job"] = job_ids.reset_index(drop=True)
    data[numeric_columns] = numeric.reset_index(drop=True)
    data[due_col] = due_hours.reset_index(drop=True).astype(float)
    data[ready_col] = ready_hours.reset_index(drop=True).astype(float)
    data["_seq"] = range(len(data))
    if optimized:
        data = data.sort_values(["\u00d6ncelik", "Teslim (saat)", "Malzeme (saat)", "_seq"], ascending=[False, True, True, True], kind="stable")
    work_items = [job for _, job in data.iterrows()]

    available = {machine: 0.0 for machine in machines}
    rows = []
    for job in work_items:
        capable = [m for m, operations in machines.items() if job["Operasyon"] in operations]
        if not capable:
            raise ValueError(f"{job['Job']} için uygun makine yok ({job['Operasyon']}).")
        ready = float(job["Malzeme (saat)"])
        setup = float(job["Hazırlık (saat)"])
        process = float(job["Süre (saat)"])
        requested_machine = job.get("Assigned machine", "")
        requested_machine = "" if pd.isna(requested_machine) else str(requested_machine).strip()
        if requested_machine and requested_machine not in capable:
            raise ValueError(f"{job['Job']} ({job['Operasyon']}) is not compatible with {requested_machine}.")
        machine = requested_machine or min(capable, key=lambda m: (max(available[m], ready) + setup + process, max(available[m], ready), m))
        setup_start = max(available[machine], ready)
        process_start = setup_start + setup
        end = process_start + process
        available[machine] = end
        rows.append({
            "Job": job["Job"],
            "Component": job["Component"] if "Component" in job.index else job["Job"],
            "Operasyon": job["Operasyon"], "Makine": machine,
            "Hazırlık başlangıç": base_time + timedelta(hours=setup_start),
            "İşlem başlangıç": base_time + timedelta(hours=process_start),
            "Bitiş": base_time + timedelta(hours=end),
            "Hazırlık başlangıç (saat)": setup_start,
            "İşlem başlangıç (saat)": process_start,
            "Bitiş (saat)": end, "Hazırlık": setup, "İşlem": process,
            "Öncelik": int(job["Öncelik"]), "Teslim (saat)": float(job["Teslim (saat)"]),
            "Malzeme (saat)": ready,
        })
    return pd.DataFrame(rows)


def plan_metrics(plan: pd.DataFrame, horizon_hours: float, machine_count: int) -> dict[str, float]:
    """Metrics over the caller-supplied plan horizon."""
    if horizon_hours < 0 or machine_count <= 0:
        raise ValueError("Ufuk negatif olamaz ve makine sayısı pozitif olmalıdır.")
    processing = float(plan["İşlem"].sum()) if len(plan) else 0.0
    setup = float(plan["Hazırlık"].sum()) if len(plan) else 0.0
    busy = processing + setup
    if horizon_hours == 0 and busy > 0:
        raise ValueError("Job yükü bulunan plan için ufuk sıfır olamaz.")
    capacity = horizon_hours * machine_count
    return {
        "processing_hours": processing,
        "setup_hours": setup,
        "utilization_pct": 100 * busy / capacity if capacity else 0.0,
        "idle_hours": capacity - busy,
        "makespan_hours": float(plan["Bitiş (saat)"].max()) if len(plan) else 0.0,
    }


def common_horizon(*plans: pd.DataFrame) -> float:
    """Return the same finish-time horizon for comparisons of multiple plans."""
    finishes = [float(p["Bitiş (saat)"].max()) for p in plans if len(p)]
    return max(finishes, default=0.0)
