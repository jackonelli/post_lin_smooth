"""Iterated posterior linearisation filter"""
from src.smoother.base import Smoother
from src.smoother.slr import SigmaPointSlrSmoother
from src.filter.slr import SigmaPointSlrFilter
from src.slr.sigma_points import SigmaPointSlr


class Ipls(Smoother):
    """Iterated posterior linearisation filter"""

    def __init__(self, motion_model, meas_model, num_iter):
        super().__init__()
        self.motion_model = motion_model
        self.meas_model = meas_model
        self._slr = SigmaPointSlr()
        self._current_estimates = None
        self.num_iter = num_iter

    def _motion_lin(self, _state, _cov, time_step):
        means, covs = self._current_estimates
        return self._slr.linear_params(self.motion_model.map_set, means[time_step], covs[time_step])

    def filter_and_smooth(self, measurements, x_0_0, P_0_0):
        """Overrides (extends) the base class default implementation"""
        initial_xs, initial_Ps, xf, Pf = self._first_iter(measurements, x_0_0, P_0_0)
        self._update_estimates(initial_xs, initial_Ps)

        current_xs, current_Ps = initial_xs, initial_Ps
        for iter_ in range(2, self.num_iter):
            self._log.info(f"Iter: {iter_}")
            current_xs, current_Ps, xf, Pf = super().filter_and_smooth(measurements, current_xs[0], current_Ps[0])
            self._update_estimates(current_xs, current_Ps)
        return current_xs, current_Ps, xf, Pf

    def _first_iter(self, measurements, x_0_0, P_0_0):
        self._log.info("Iter: 1")
        smoother = SigmaPointSlrSmoother(self.motion_model, self.meas_model)
        return smoother.filter_and_smooth(measurements, x_0_0, P_0_0)

    def _filter_seq(self, measurements, x_0_0, P_0_0):
        return SigmaPointSlrFilter(self.motion_model, self.meas_model).filter_seq(measurements, x_0_0, P_0_0)

    def _update_estimates(self, means, covs):
        self._current_estimates = (means, covs)