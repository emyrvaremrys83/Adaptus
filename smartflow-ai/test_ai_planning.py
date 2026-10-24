from datetime import datetime
import unittest

import pandas as pd

from ai_planning import compare_schedule_outcomes, jobs_with_ai_durations
from ai_predictor import PROCESS, SETUP
from planner import build_plan


class AIPlanningTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 10, 24, 8)
        self.jobs = pd.DataFrame([
            {"Job": "A", "Component": "Part A", "Operasyon": "Torna", PROCESS: 2., SETUP: 0.,
             "Öncelik": 5, "Teslim (saat)": 2., "Malzeme (saat)": 0., "Assigned machine": "Lathe-01"},
            {"Job": "B", "Component": "Part B", "Operasyon": "Torna", PROCESS: 1., SETUP: .5,
             "Öncelik": 4, "Teslim (saat)": 4., "Malzeme (saat)": 0., "Assigned machine": ""},
            {"Job": "C", "Component": "Part C", "Operasyon": "Freze", PROCESS: 1., SETUP: .5,
             "Öncelik": 3, "Teslim (saat)": 6., "Malzeme (saat)": 3., "Assigned machine": ""},
        ])

    def test_ai_copy_preserves_all_original_inputs_except_processing(self):
        before = self.jobs.copy(deep=True)
        estimated = jobs_with_ai_durations(self.jobs)
        pd.testing.assert_frame_equal(self.jobs, before)
        pd.testing.assert_frame_equal(estimated.drop(columns=PROCESS), self.jobs.drop(columns=PROCESS))
        self.assertFalse(estimated[PROCESS].equals(self.jobs[PROCESS]))
        # Repeated runs start from stored estimates, never from prior predictions.
        pd.testing.assert_frame_equal(estimated, jobs_with_ai_durations(self.jobs))

    def test_lateness_includes_queue_delay_and_matches_by_job_id(self):
        original = build_plan(self.jobs, optimized=True, base_time=self.start)
        changed = self.jobs.copy()
        changed.loc[0, PROCESS] = 3.
        estimated = build_plan(changed, optimized=True, base_time=self.start)
        outcomes = compare_schedule_outcomes(original, estimated.iloc[::-1], self.start).set_index("Job")
        # A originally finishes exactly at its deadline; that is on time.
        self.assertEqual(outcomes.loc["A", "Original delay (h)"], 0.)
        self.assertEqual(outcomes.loc["A", "AI delay (h)"], 1.)
        # B's processing estimate is unchanged, but it waits behind A.
        self.assertEqual(outcomes.loc["B", "Finish shift (h)"], 1.)
        self.assertEqual(outcomes.loc["B", "AI delay (h)"], .5)
        self.assertEqual(outcomes.loc["C", "Finish shift (h)"], 0.)
        self.assertEqual(int(outcomes["Newly late"].sum()), 2)

    def test_ai_plan_preserves_readiness_setup_and_machine_constraints(self):
        plan = build_plan(jobs_with_ai_durations(self.jobs), optimized=True, base_time=self.start)
        self.assertEqual(plan.set_index("Job").loc["A", "Makine"], "Lathe-01")
        self.assertAlmostEqual(plan["Hazırlık"].sum(), self.jobs[SETUP].sum())
        for _, group in plan.groupby("Makine"):
            previous_end = 0.
            for row in group.sort_values("Hazırlık başlangıç (saat)").to_dict("records"):
                self.assertGreaterEqual(row["Hazırlık başlangıç (saat)"], max(previous_end, row["Malzeme (saat)"]))
                previous_end = row["Bitiş (saat)"]

    def test_empty_plan_and_mismatched_job_sets(self):
        empty_jobs = self.jobs.iloc[:0]
        empty_plan = build_plan(jobs_with_ai_durations(empty_jobs), base_time=self.start)
        self.assertTrue(compare_schedule_outcomes(empty_plan, empty_plan, self.start).empty)
        full_plan = build_plan(self.jobs, base_time=self.start)
        with self.assertRaises(ValueError):
            compare_schedule_outcomes(full_plan, empty_plan, self.start)
        with self.assertRaises(ValueError):
            compare_schedule_outcomes(full_plan, full_plan.iloc[:1], self.start)

    def test_absolute_due_dates_and_already_late_jobs(self):
        jobs = self.jobs.copy()
        jobs["Due at"] = ["2026-10-24T07:00", "2026-10-24T12:00", "2026-10-24T14:00"]
        jobs["Material ready at"] = ["2026-10-24T06:00", "2026-10-24T08:00", "2026-10-24T11:00"]
        original = build_plan(jobs, optimized=True, base_time=self.start)
        estimated = build_plan(jobs_with_ai_durations(jobs), optimized=True, base_time=self.start)
        outcomes = compare_schedule_outcomes(original, estimated, self.start).set_index("Job")
        self.assertEqual(outcomes.loc["A", "Original delay (h)"], 3.)
        self.assertFalse(outcomes.loc["A", "Newly late"])
