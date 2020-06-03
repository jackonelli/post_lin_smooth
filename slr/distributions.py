"""Distribution interfaces for SLR"""
from abc import ABC, abstractmethod
import numpy as np
from scipy.stats import multivariate_normal as mvn
from post_lin_smooth.analytics import pos_def_check


class Prior(ABC):
    """Prior distribution p(x)
    This prior should in principle be a Gaussian
    but some modifications might be necessary to fulfill
    constraints in the approximated process.
    """
    @abstractmethod
    def __init__(self, x_bar, P):
        pass

    @abstractmethod
    def sample(self, num_samples):
        pass


class Conditional(ABC):
    """Conditional distribution p(z | x)"""
    @abstractmethod
    def sample(self, x_sample, num_samples: int):
        pass


class Gaussian(Prior):
    """Gaussian distribution"""
    def __init__(self, x_bar, P):
        self.x_bar = x_bar
        self.P = P

    def sample(self, num_samples):
        return mvn.rvs(mean=self.x_bar, cov=self.P, size=num_samples)
