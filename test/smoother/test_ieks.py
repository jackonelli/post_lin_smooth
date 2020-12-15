"""Test EKS
Check that the EKS implementation matches the one in the paper:

"Levenberg-marquardt and line-search extended kalman smoother"

Runs EKS and compares with stored matlab output.
"""
import unittest
import numpy as np
from src.smoother.ieks import Ieks
from src.models.range_bearing import MultiSensorRange
from src.models.coord_turn import LmCoordTurn
from data.lm_ieks_paper.coord_turn_example import get_specific_states_from_file, Type
from pathlib import Path


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
        motion_model = LmCoordTurn(dt, Q)

        sens_pos_1 = np.array([-1.5, 0.5])
        sens_pos_2 = np.array([1, 1])
        sensors = np.row_stack((sens_pos_1, sens_pos_2))
        std = 0.5
        R = std ** 2 * np.eye(2)
        meas_model = MultiSensorRange(sensors, R)

        prior_mean = np.array([0, 0, 1, 0, 0])
        prior_cov = np.diag([0.1, 0.1, 1, 1, 1])

        _, measurements, ss_xf, ss_xs = get_specific_states_from_file(Path.cwd() / "data/lm_ieks_paper", Type.GN)
        ieks = Ieks(motion_model, meas_model, num_iter=10)
        xf, Pf, xs, Ps = ieks.filter_and_smooth(measurements, prior_mean, prior_cov)
        np.allclose(xf, ss_xf, rtol=1e-5, atol=1)
        np.allclose(xs, ss_xs, rtol=1e-2, atol=1)
