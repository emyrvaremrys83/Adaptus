import unittest

import pandas as pd

from planner import MACHINES, build_plan, common_horizon, plan_metrics


def jobs_fixture():
    return pd.DataFrame([
        {"Job": "JOB-A", "Operasyon": "Torna", "Süre (saat)": 3, "Hazırlık (saat)": 1, "Öncelik": 2, "Teslim (saat)": 10, "Malzeme (saat)": 4},
        {"Job": "JOB-B", "Operasyon": "Freze", "Süre (saat)": 2, "Hazırlık (saat)": 0.5, "Öncelik": 5, "Teslim (saat)": 8, "Malzeme (saat)": 0},
        {"Job": "JOB-C", "Operasyon": "Montaj", "Süre (saat)": 4, "Hazırlık (saat)": 0.5, "Öncelik": 3, "Teslim (saat)": 12, "Malzeme (saat)": 2},
    ])


class PlannerTests(unittest.TestCase):
    def test_machine_eligibility_and_material_ready(self):
        plan = build_plan(jobs_fixture())
        for row in plan.to_dict("records"):
            self.assertIn(row["Operasyon"], MACHINES[row["Makine"]])
            self.assertGreaterEqual(row["Hazırlık başlangıç (saat)"], row["Malzeme (saat)"])

    def test_no_machine_overlap_and_setup_separate(self):
        plan = build_plan(jobs_fixture())
        self.assertAlmostEqual(float(plan["Hazırlık"].sum()), 2.0)
        for _, group in plan.sort_values("Hazırlık başlangıç (saat)").groupby("Makine"):
            intervals = group.sort_values("Hazırlık başlangıç (saat)")
            previous_end = 0.0
            for row in intervals.to_dict("records"):
                self.assertGreaterEqual(row["Hazırlık başlangıç (saat)"], previous_end)
                previous_end = row["Bitiş (saat)"]

    def test_comparison_uses_same_jobs_and_common_horizon(self):
        jobs = jobs_fixture()
        baseline, optimized = build_plan(jobs), build_plan(jobs, optimized=True)
        self.assertEqual(set(baseline["Job"]), set(optimized["Job"]))
        horizon = common_horizon(baseline, optimized)
        a = plan_metrics(baseline, horizon, len(MACHINES))
        b = plan_metrics(optimized, horizon, len(MACHINES))
        self.assertEqual(a["idle_hours"] + a["processing_hours"] + a["setup_hours"], horizon * len(MACHINES))
        self.assertAlmostEqual(a["utilization_pct"], b["utilization_pct"])

    def test_ineligible_operation_is_reported(self):
        job = jobs_fixture().iloc[:1].copy()
        job.loc[:, "Operasyon"] = "Kaynak"
        with self.assertRaisesRegex(ValueError, "uygun makine yok"):
            build_plan(job)


if __name__ == "__main__":
    unittest.main()
