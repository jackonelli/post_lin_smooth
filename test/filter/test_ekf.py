"""Test EKF
Check that the EKF implementation matches the one in the paper:

"Levenberg-marquardt and line-search extended kalman smoother"

Runs EKF and compares with stored matlab output.
"""
import unittest
import numpy as np
from src.filter.ekf import Ekf
from src.models.range_bearing import MultiSensorRange
from src.models.coord_turn import LmCoordTurn
from data.lm_coord_turn_example import get_specific_states_from_file
from pathlib import Path


class TestEkf(unittest.TestCase):
    def test_cmp_with_ss_impl(self):
        seed = 2
        np.random.seed(seed)
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
        motion_model = LmCoordTurn(dt, Q)

        sens_pos_1 = np.array([-1.5, 0.5])
        sens_pos_2 = np.array([1, 1])
        sensors = np.row_stack((sens_pos_1, sens_pos_2))
        std = 0.5
        R = std ** 2 * np.eye(2)
        meas_model = MultiSensorRange(sensors, R)

        prior_mean = np.array([0, 0, 1, 0, 0])
        prior_cov = np.diag([0.1, 0.1, 1, 1, 1])

        states, measurements, ss_xf = get_specific_states_from_file(Path.cwd())
        ekf = Ekf(motion_model, meas_model)
        xf, Pf, xs, Ps = ekf.filter_seq(measurements, prior_mean, prior_cov)
        self.assertTrue(np.allclose(xf, ss_xf))
