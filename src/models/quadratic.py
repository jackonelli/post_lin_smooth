"""Quadratic meas model"""
import numpy as np
from src.models.base import MeasModel, Differentiable


class Quadratic(MeasModel, Differentiable):
    """
    state is
        x_k = actual state at time step k
    """

    def __init__(self, coeff: float, meas_noise):
        # Rename? 'scale' perhaps
        self.coeff = coeff
        self._meas_noise = np.atleast_2d(meas_noise)

    def mapping(self, state, time_step=None):
        return state ** 2 * self.coeff

    def meas_noise(self, _time_step):
        return self._meas_noise

    def jacobian(self, state, _time_step=None):
        return np.atleast_2d(2 * state * self.coeff)
