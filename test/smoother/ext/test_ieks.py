"""Test (GN-)IEKS
Check that the (GN-)IEKS implementation matches the one in the paper:

"Levenberg-marquardt and line-search extended kalman smoother"

Runs (GN-)IEKS and compares with stored matlab output.
"""
import unittest
from pathlib import Path
from functools import partial
import numpy as np
from src.smoother.ext.ieks import Ieks
from src.cost_fn.ext import analytical_smoothing_cost
from src.models.range_bearing import MultiSensorRange
from src.models.coord_turn import CoordTurn
from data.lm_ieks_paper.coord_turn_example import get_specific_states_from_file, Type


class TestIeks(unittest.TestCase):
    def test_cmp_with_ss_impl(self):
        dt = 0.01
        qc = 0.01
        qw = 10
        Q = np.array(
            [
                [qc * dt ** 3 / 3, 0, qc * dt ** 2 / 2, 0, 0],
                [0, qc * dt ** 3 / 3, 0, qc * dt ** 2 / 2, 0],
                [qc * dt ** 2 / 2, 0, qc * dt, 0, 0],
                [0, qc * dt ** 2 / 2, 0, qc * dt, 0],
                [0, 0, 0, 0, dt * qw],
            ]
        )
        motion_model = CoordTurn(dt, Q)

        sens_pos_1 = np.array([-1.5, 0.5])
        sens_pos_2 = np.array([1, 1])
        sensors = np.row_stack((sens_pos_1, sens_pos_2))
        std = 0.5
        R = std ** 2 * np.eye(2)
        meas_model = MultiSensorRange(sensors, R)

        prior_mean = np.array([0, 0, 1, 0, 0])
        prior_cov = np.diag([0.1, 0.1, 1, 1, 1])

        num_iter = 1
        _, measurements, ss_mf, ss_ms = get_specific_states_from_file(
            Path.cwd() / "data/lm_ieks_paper", Type.GN, num_iter
        )
        measurements = measurements[:, :2]

        cost_fn = partial(
            analytical_smoothing_cost,
            measurements=measurements,
            m_1_0=prior_mean,
            P_1_0=prior_cov,
            motion_model=motion_model,
            meas_model=meas_model,
        )

        K = measurements.shape[0]
        init_traj = (np.zeros((K, prior_mean.shape[0])), None)
        ieks = Ieks(motion_model, meas_model, num_iter)
        mf, Pf, ms, Ps, _iter_cost = ieks.filter_and_smooth_with_init_traj(
            measurements, prior_mean, prior_cov, init_traj, 1, cost_fn
        )
        self.assertTrue(np.allclose(mf, ss_mf))
        self.assertTrue(np.allclose(ms, ss_ms))

        num_iter = 10
        _, measurements, ss_mf, ss_ms = get_specific_states_from_file(
            Path.cwd() / "data/lm_ieks_paper", Type.GN, num_iter
        )
        measurements = measurements[:, :2]

        ieks = Ieks(motion_model, meas_model, num_iter=num_iter)
        mf, Pf, ms, Ps, _iter_cost = ieks.filter_and_smooth_with_init_traj(
            measurements, prior_mean, prior_cov, init_traj, 1, cost_fn
        )
        self.assertTrue(np.allclose(mf, ss_mf))
        self.assertTrue(np.allclose(ms, ss_ms))
