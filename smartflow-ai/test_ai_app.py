"""Exercise the duration toggle against isolated copies of saved jobs."""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import tempfile
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

from ai_predictor import PROCESS


class AIAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous_logging = logging.root.manager.disable
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        logging.disable(cls.previous_logging)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="smartflow-ai-tests-")
        self.root = Path(self.temp.name)
        source = Path(__file__).parent
        for name in ("app.py", "planner.py", "ai_predictor.py", "ai_planning.py", "ai_panel.py", "plan_impact.py", "jobs.json"):
            shutil.copy2(source / name, self.root / name)
        shutil.copytree(source / "timeline_navigation", self.root / "timeline_navigation")

    def tearDown(self):
        self.temp.cleanup()

    def test_toggle_round_trip_for_three_demos_in_both_languages(self):
        for language in ("English", "Türkçe"):
            at = AppTest.from_file(str(self.root / "app.py"))
            at.session_state["language"] = language
            at.run(timeout=30)
            previous_impact = None
            for variant, total in (("short", 22.), ("medium", 44.), ("long", 88.)):
                with self.subTest(language=language, variant=variant):
                    at.button(key="demo_jobs_" + variant).click().run(timeout=30)
                    self.assertFalse(at.exception)
                    self.assertFalse(at.error)
                    self.assertEqual(at.session_state["jobs"][PROCESS].sum(), total)
                    stored = (self.root / "jobs.json").read_bytes()
                    original_jobs = at.session_state["jobs"].copy(deep=True)
                    impact = json.loads(next(chart for chart in at.get("plotly_chart") if chart.key == "ai-impact-map").proto.spec)
                    if previous_impact is not None:
                        self.assertNotEqual(previous_impact["data"], impact["data"])
                    previous_impact = impact
                    before = [json.loads(chart.proto.spec) for chart in at.get("plotly_chart") if chart.key.startswith("gantt-")]
                    original_metric = at.metric[0].value
                    at.toggle(key="use_ai_durations").set_value(True).run(timeout=30)
                    self.assertFalse(at.exception)
                    self.assertFalse(at.error)
                    after = [json.loads(chart.proto.spec) for chart in at.get("plotly_chart") if chart.key.startswith("gantt-")]
                    self.assertEqual(len(after), 2)
                    self.assertEqual(impact["data"], json.loads(next(chart for chart in at.get("plotly_chart") if chart.key == "ai-impact-map").proto.spec)["data"])
                    for old, new in zip(before, after):
                        self.assertNotEqual(old["data"], new["data"])
                        self.assertEqual(old["layout"]["xaxis"]["range"], new["layout"]["xaxis"]["range"])
                    self.assertNotEqual(original_metric, at.metric[0].value)
                    pd.testing.assert_frame_equal(at.session_state["jobs"], original_jobs)
                    self.assertEqual(stored, (self.root / "jobs.json").read_bytes())
                    at.toggle(key="use_ai_durations").set_value(False).run(timeout=30)
                    restored = [json.loads(chart.proto.spec) for chart in at.get("plotly_chart") if chart.key.startswith("gantt-")]
                    self.assertEqual([c["data"] for c in before], [c["data"] for c in restored])
                    self.assertEqual(original_metric, at.metric[0].value)
                    self.assertEqual(stored, (self.root / "jobs.json").read_bytes())

    def test_empty_jobs_disables_ai_without_errors(self):
        (self.root / "jobs.json").write_text("[]", encoding="utf-8")
        at = AppTest.from_file(str(self.root / "app.py")).run(timeout=30)
        self.assertFalse(at.exception)
        self.assertFalse(at.error)
        self.assertTrue(at.toggle(key="use_ai_durations").disabled)
        self.assertFalse(at.toggle(key="use_ai_durations").value)

    def test_demo_switch_with_ai_enabled_keeps_original_data_on_disk(self):
        at = AppTest.from_file(str(self.root / "app.py")).run(timeout=30)
        at.toggle(key="use_ai_durations").set_value(True).run(timeout=30)
        for variant, total in (("short", 22.), ("long", 88.)):
            at.button(key="demo_jobs_" + variant).click().run(timeout=30)
            self.assertFalse(at.exception)
            self.assertFalse(at.error)
            self.assertTrue(at.toggle(key="use_ai_durations").value)
            records = json.loads((self.root / "jobs.json").read_text(encoding="utf-8"))
            self.assertAlmostEqual(sum(row[PROCESS] for row in records), total)
            self.assertEqual(at.session_state["jobs"][PROCESS].sum(), total)

    def test_delivery_table_flags_new_late_jobs_and_follows_active_mode(self):
        from ai_predictor import SETUP

        start = datetime.now().replace(minute=0, second=0, microsecond=0)
        rows = []
        for job, operation, duration, setup, priority, due in (
            ("A", "Torna", 2., 0., 5, 2.),
            ("B", "Torna", 1., .5, 4, 3.5),
            ("C", "Freze", 1., 0., 3, 12.),
        ):
            rows.append({"Job": job, "Component": job, "Operasyon": operation,
                         PROCESS: duration, SETUP: setup, "Öncelik": priority, "Assigned machine": "",
                         "Due at": (start + timedelta(hours=due)).isoformat(),
                         "Material ready at": start.isoformat()})
        (self.root / "jobs.json").write_text(json.dumps(rows), encoding="utf-8")
        at = AppTest.from_file(str(self.root / "app.py")).run(timeout=30)
        self.assertFalse(at.exception)
        self.assertTrue(any("No late jobs" in element.value for element in at.success))
        at.toggle(key="use_ai_durations").set_value(True).run(timeout=30)
        self.assertFalse(at.exception)
        at.radio(key="ai_impact_filter").set_value("new").run(timeout=30)
        impact = json.loads(next(chart for chart in at.get("plotly_chart") if chart.key == "ai-impact-map").proto.spec)
        self.assertEqual({job for trace in impact["data"] for job in trace["y"]}, {"A", "B"})
        at.selectbox(key="ai_impact_job").set_value("B").run(timeout=30)
        self.assertTrue(any("This job first misses" in item.value for item in at.warning))
        at.radio(key="ai_impact_filter").set_value("all").run(timeout=30)
        impact = json.loads(next(chart for chart in at.get("plotly_chart") if chart.key == "ai-impact-map").proto.spec)
        self.assertEqual({job for trace in impact["data"] for job in trace["y"]}, {"A", "B", "C"})
        delivery = next(item.value for item in at.dataframe if "Active plan status" in item.value.columns)
        self.assertEqual(set(delivery["Job"]), {"A", "B"})
        self.assertEqual(set(delivery["Active plan status"]), {"Newly late (AI)"})
        self.assertTrue((delivery["Delay · original (h)"] == 0).all())
        self.assertTrue((delivery["Delay · AI (h)"] > 0).all())
        at.checkbox(key="show_late_jobs_only").set_value(False).run(timeout=30)
        delivery = next(item.value for item in at.dataframe if "Active plan status" in item.value.columns)
        self.assertEqual(len(delivery), 3)
        self.assertEqual(delivery.set_index("Job").loc["C", "Active plan status"], "On time")
        at.toggle(key="use_ai_durations").set_value(False).run(timeout=30)
        delivery = next(item.value for item in at.dataframe if "Active plan status" in item.value.columns)
        self.assertEqual(set(delivery["Active plan status"]), {"On time"})
