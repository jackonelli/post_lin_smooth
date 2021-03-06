"""Cubic meas model"""
import numpy as np
from src.models.base import MeasModel, Differentiable


class Cubic(MeasModel, Differentiable):
    """
    state is
        x_k = actual state at time step k
    """

    def __init__(self, coeff: float, proc_noise):
        # Rename? 'scale' perhaps
        self.coeff = coeff
        self._proc_noise = proc_noise

    def mapping(self, state, time_step=None):
        return state ** 3 * self.coeff

    def meas_noise(self, _time_step):
        return self._proc_noise

    def jacobian(self, state, time_step=None):
        return 3 * state ** 2 * self.coeff
