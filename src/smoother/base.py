"""Abstract smoother class"""
from abc import abstractmethod, ABC
import logging
import numpy as np
from src.filter.base import Filter


class Smoother(ABC):
    """Abstract smoother class

    Assumes motion and meas model on the form:
        x_k = f(x_{k-1}) + q_k, q_k ~ N(0, Q_k)
        y_k = f(x_k}) + r_k, r_k ~ N(0, R_k).
    """

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)

    def filter_and_smooth(self, measurements, m_1_0, P_1_0):
        """Filters and smooths a measurement sequence.

        Args:

        Returns:
            filter_means (K, D_x): Filtered mean estimates for times 1,..., K
            filter_covs (K, D_x, D_x): Filtered covariance estimates for times 1,..., K
            smooth_means (K, D_x): Smoothed mean estimates for times 1,..., K
            smooth_covs (K, D_x, D_x): Smoothed covariance estimates for times 1,..., K
        """

        filter_means, filter_covs, pred_means, pred_covs = self._filter_seq(measurements, m_1_0, P_1_0)
        smooth_means, smooth_covs = self.smooth_seq_pre_comp_filter(filter_means, filter_covs, pred_means, pred_covs)
        return filter_means, filter_covs, smooth_means, smooth_covs

    def smooth_seq_pre_comp_filter(self, filter_means, filter_covs, pred_means, pred_covs):
        """Smooths the outputs from a filter.

        Args:
            filter_means (K, D_x): Filtered estimates for times 1,..., K
            filter_covs (K, D_x, D_x): Filtered covariance estimates for times 1,..., K
            pred_means (K, D_x): Predicted estimates for times 1,..., K
            pred_covs (K, D_x, D_x): Predicted covariance estimates for times 1,..., K

        Returns:
            smooth_means (K, D_x): Smoothed estimates for times 1,..., K
            smooth_covs (K, D_x, D_x): Smoothed covariance estimates for times 1,..., K
        """

        K = filter_means.shape[0]
        smooth_means, smooth_covs = self._init_smooth_estimates(filter_means[-1, :], filter_covs[-1, :, :], K)
        for k in np.flip(np.arange(1, K)):
            m_kminus1_kminus1 = filter_means[k - 1, :]
            P_kminus1_kminus1 = filter_covs[k - 1, :, :]
            m_k_K, P_k_K = smooth_means[k, :], smooth_covs[k, :, :]
            m_k_kminus1, P_k_kminus1 = pred_means[k, :], pred_covs[k, :, :]
            m_kminus1_K, P_kminus1_K = self._rts_update(
                m_k_K,
                P_k_K,
                m_kminus1_kminus1,
                P_kminus1_kminus1,
                m_k_kminus1,
                P_k_kminus1,
                self._motion_lin(m_kminus1_kminus1, P_kminus1_kminus1, k - 1),
            )
            smooth_means[k - 1, :] = m_kminus1_K
            smooth_covs[k - 1, :, :] = P_kminus1_K
        return smooth_means, smooth_covs

    @abstractmethod
    def _filter_seq(self, measurements, m_1_0, P_1_0):
        """Filter sequence

        Technically smoothers do not require the ability to filter.
        Given a motion model and filtered and predicted estimates,
        the smooth estimates can be calculated without an explicit filter and meas model.
        However, a concrete implementation of a smoother, e.g. the RTS smoother,
        is expected to smooth estimates coming from a KF, not some other filter.

        The API still allows for smoothing of any filter sequence by using the `smooth_seq_pre_comp_filter` method
        """
        pass

    def _rts_update(self, m_k_K, P_k_K, m_kminus1_kminus1, P_kminus1_kminus1, m_k_kminus1, P_k_kminus1, linear_params):
        """RTS update step
        Args:
            m_k_K: m_{k|K}
            P_k_K: P_{k|K}
            m_kminus1_kminus1: m_{k-1 | k-1}
            P_kminus1_kminus1: P_{k-1 | k-1}
            m_k_kminus1: m_{k | k-1}
            P_k_kminus1: P_{k | k-1}
            linearization (tuple): (A, b, Q) param's for linear (affine) approx

        Returns:
            m_kminus1_K: m_{k-1 | K}
            P_kminus1_K: P_{k-1 | K}
        """
        A, _, Q = linear_params

        G_k = P_kminus1_kminus1 @ A.T @ np.linalg.inv(P_k_kminus1)
        m_kminus1_K = m_kminus1_kminus1 + G_k @ (m_k_K - m_k_kminus1)
        P_kminus1_K = P_kminus1_kminus1 + G_k @ (P_k_K - P_k_kminus1) @ G_k.T
        return m_kminus1_K, P_kminus1_K

    @staticmethod
    def _init_smooth_estimates(m_K_K, P_K_K, K):
        D_x = m_K_K.shape[0]
        smooth_means = np.empty((K, D_x))
        smooth_covs = np.empty((K, D_x, D_x))
        smooth_means[-1, :] = m_K_K
        smooth_covs[-1, :, :] = P_K_K
        return smooth_means, smooth_covs

    @abstractmethod
    def _motion_lin(state, cov, time_step):
        """Linearise motion model

        Time step k gives required context for some linearisations (Posterior SLR).
        """
        pass
