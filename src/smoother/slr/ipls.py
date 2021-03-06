"""Sigma point Iterated posterior linearisation smoother (IPLS)"""
from src.smoother.base import IteratedSmoother
from src.smoother.slr.prls import SigmaPointPrLs
from src.filter.iplf import SigmaPointIplf
from src.slr.sigma_points import SigmaPointSlr
import numpy as np


class SigmaPointIpls(IteratedSmoother):
    """Iterated posterior linearisation filter"""

    def __init__(self, motion_model, meas_model, sigma_point_method, num_iter):
        super().__init__()
        self._motion_model = motion_model
        self._meas_model = meas_model
        self._slr = SigmaPointSlr(sigma_point_method)
        self._sigma_point_method = sigma_point_method
        self._current_means = None
        self._current_covs = None
        self.num_iter = num_iter

    def _motion_lin(self, _mean, _cov, time_step):
        return self._slr.linear_params(
            self._mapping_with_time_step(self._motion_model.map_set, time_step=time_step),
            self._current_means[time_step],
            self._current_covs[time_step],
        )

    def _first_iter(self, measurements, m_1_0, P_1_0, cost_fn):
        self._log.info("Iter: 1")
        smoother = SigmaPointPrLs(self._motion_model, self._meas_model, self._sigma_point_method)
        return smoother.filter_and_smooth(measurements, m_1_0, P_1_0, cost_fn)

    def _filter_seq(self, measurements, m_1_0, P_1_0):
        iplf = SigmaPointIplf(self._motion_model, self._meas_model, self._sigma_point_method)
        iplf._update_estimates(self._current_means, self._current_covs)
        return iplf.filter_seq(measurements, m_1_0, P_1_0)

    def _update_estimates(self, means, covs):
        self._current_means = means.copy()
        self._current_covs = covs.copy()
