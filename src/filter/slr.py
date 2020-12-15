"""SLR filter"""
from src.filter.base import Filter
from src.slr.sigma_points import SigmaPointSlr


class SigmaPointSlrFilter(Filter):
    """Sigma point SLR filter"""

    def __init__(self, motion_model, meas_model):
        self._motion_model = motion_model
        self._meas_model = meas_model
        self._slr = SigmaPointSlr()

    def _motion_lin(self, mean, cov, _time_step):
        return self._slr.linear_params(self._motion_model.map_set, mean, cov)

    def _meas_lin(self, mean, cov, _time_step):
        return self._slr.linear_params(self._meas_model.map_set, mean, cov)

    def _proc_noise(self, time_step):
        return self._motion_model.proc_noise(time_step)

    def _meas_noise(self, time_step):
        return self._meas_model.meas_noise(time_step)
