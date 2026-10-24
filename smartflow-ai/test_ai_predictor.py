import unittest

import numpy as np
import pandas as pd

from ai_predictor import OPERATIONS, PROCESS, SETUP, predict_hours, train_demo_model


class PredictorTests(unittest.TestCase):
    def test_held_out_error_improves_on_original_estimates(self):
        _, report = train_demo_model()
        self.assertLess(report['model_mae'], report['baseline_mae'])
        self.assertEqual(report['test_rows'], 600)

    def test_predictions_cover_supported_bounds_without_mutating_jobs(self):
        jobs = pd.DataFrame([{'Operasyon': op, PROCESS: hours, SETUP: setup}
                             for op in OPERATIONS for hours in [.5, 48] for setup in [0, 12]])
        before = jobs.copy(deep=True)
        predicted = predict_hours(jobs)
        self.assertTrue(np.isfinite(predicted).all())
        self.assertTrue((predicted > 0).all())
        pd.testing.assert_frame_equal(before, jobs)

    def test_rejects_unsupported_inputs(self):
        for op, hours in [('Unknown', 4), ('Torna', float('nan')), ('Torna', -1)]:
            with self.assertRaises(ValueError):
                predict_hours(pd.DataFrame([{'Operasyon': op, PROCESS: hours, SETUP: .5}]))

    def test_empty_jobs(self):
        self.assertEqual(len(predict_hours(pd.DataFrame(columns=['Operasyon', PROCESS, SETUP]))), 0)
