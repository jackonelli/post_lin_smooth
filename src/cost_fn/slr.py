"""SLR cost functions"""
import logging
from functools import partial
import numpy as np
from src.models.base import MotionModel, MeasModel
from src.slr.base import Slr

LOGGER = logging.getLogger(__name__)


def slr_smoothing_cost_pre_comp(
    traj, measurements, m_1_0, P_1_0_inv, motion_bar, meas_bar, motion_cov_inv, meas_cov_inv
):
    """Cost function for an optimisation problem used in the family of slr smoothers

    GN optimisation of this cost function will result in a linearised function
    corresponding to the SLR Smoother (PrLS, PLS) et al.

    Args:
        traj: states for a time sequence 1, ..., K
            represented as a np.array(K, D_x).
            (The actual variable in the cost function)
        measurements: measurements for a time sequence 1, ..., K
            represented as a list of length K of np.array(D_y,)
        m_1_0 (D_x,): Prior mean for time 1
        P_1_0_inv (D_x, D_x): Inverse prior covariance for time 1
        motion_bar: estimated SLR expectation for the motion model for a time sequence 1, ..., K
            represented as a list of length K of np.array(D_x,)
        meas_bar: estimated SLR expectation for the meas model for a time sequence 1, ..., K
            represented as a list of length K of np.array(D_y,)
        motion_cov_inv: estimated inverse covariances (Omega_k + Q_k) for a time sequence 1, ..., K
            represented as a list of length K of np.array(D_x, D_x)
        meas_cov_inv: estimated inverse covariances (Lambda_k + R_k) for a time sequence 1, ..., K
            represented as a list of length K of np.array(D_x, D_x)
    """
    prior_diff = traj[0, :] - m_1_0
    _cost = prior_diff.T @ P_1_0_inv @ prior_diff

    K = len(measurements)

    for k in range(1, K + 1):
        k_ind = k - 1
        if k < K:
            motion_diff_k = traj[k_ind + 1, :] - motion_bar[k_ind]
            _cost += motion_diff_k.T @ motion_cov_inv[k_ind] @ motion_diff_k
        meas_k = measurements[k_ind]
        if any(np.isnan(meas_k)):
            continue
        meas_diff_k = meas_k - meas_bar[k_ind]
        _cost += meas_diff_k.T @ meas_cov_inv[k_ind] @ meas_diff_k

    return _cost


def slr_smoothing_cost_means(
    traj, measurements, m_1_0, P_1_0_inv, estimated_covs, motion_fn, meas_fn, motion_cov_inv, meas_cov_inv, slr_method
):
    """Cost function for an optimisation problem used in the family of slr smoothers

    GN optimisation of this cost function will result in a linearised function
    corresponding to the SLR Smoother (PrLS, PLS) et al.

    The purpose of this cost function is to efficienctly emulate the fixation of the covariances
    while varying with the means.

    Args:
        traj: states for a time sequence 1, ..., K
            represented as a np.array(K, D_x).
            (The actual variable in the cost function)
        measurements: measurements for a time sequence 1, ..., K
            represented as a list of length K of np.array(D_y,)
        m_1_0 (D_x,): Prior mean for time 1
        P_1_0_inv (D_x, D_x): Inverse prior covariance for time 1
        estimated_covs: covs for a time sequence 1, ..., K
            represented as a np.array(K, D_x, D_x).
        motion_fn: MotionModel.map_set,
        meas_fn: MeasModel.map_set,
        motion_cov_inv: estimated inverse covariances (Omega_k + Q_k) for a time sequence 1, ..., K
            represented as a list of length K of np.array(D_x, D_x)
        meas_cov_inv: estimated inverse covariances (Lambda_k + R_k) for a time sequence 1, ..., K
            represented as a list of length K of np.array(D_x, D_x)
        slr_method: Slr
    """
    motion_bar = [
        slr_method.calc_z_bar(partial(motion_fn, time_step=k), mean_k, cov_k)
        for (k, (mean_k, cov_k)) in enumerate(zip(traj, estimated_covs), 1)
    ]

    meas_bar = [
        slr_method.calc_z_bar(partial(meas_fn, time_step=k), mean_k, cov_k)
        for (k, (mean_k, cov_k)) in enumerate(zip(traj, estimated_covs), 1)
    ]
    return slr_smoothing_cost_pre_comp(
        traj, measurements, m_1_0, P_1_0_inv, motion_bar, meas_bar, motion_cov_inv, meas_cov_inv
    )


def slr_smoothing_cost(
    traj,
    covs,
    measurements,
    m_1_0,
    P_1_0,
    motion_model: MotionModel,
    meas_model: MeasModel,
    slr: Slr,
):
    """Cost function for an optimisation problem used in the family of slr smoothers

    GN optimisation of this cost function will result in a linearised function
    corresponding to the SLR Smoother (PrLS, PLS) et al.

    This version is used for testing but not in the actual smoother implementations
    since it is too inefficient to recompute the SLR estimates from scratch.

    Args:
        traj: states for a time sequence 1, ..., K
            represented as a np.array(K, D_x).
            (The actual variable in the cost function)
        measurements: measurements for a time sequence 1, ..., K
            represented as a list of length K of np.array(D_y,)
        m_1_0 (D_x,): Prior mean for time 1
        P_1_0 (D_x, D_x): Prior covariance for time 1
        motion_model: MotionModel,
        meas_model: MeasModel,
        slr_method: Slr
    """
    prior_diff = traj[0, :] - m_1_0
    _cost = prior_diff.T @ np.linalg.inv(P_1_0) @ prior_diff

    motion_mapping = partial(motion_model.map_set, time_step=None)
    for k in range(0, traj.shape[0] - 1):
        mean_k = traj[k, :]
        cov_k = covs[k, :, :]
        motion_bar, psi, phi = slr.slr(motion_mapping, mean_k, cov_k)
        _, _, Omega_k = slr.linear_params_from_slr(mean_k, cov_k, motion_bar, psi, phi)

        motion_diff_k = traj[k + 1, :] - motion_bar
        _cost += motion_diff_k.T @ np.linalg.inv(motion_model.proc_noise(k) + Omega_k) @ motion_diff_k

    meas_mapping = partial(meas_model.map_set, time_step=None)
    for k in range(0, traj.shape[0]):
        if any(np.isnan(measurements[k, :])):
            continue
        mean_k = traj[k, :]
        cov_k = covs[k, :]
        meas_bar, psi, phi = slr.slr(meas_mapping, mean_k, cov_k)
        _, _, Lambda_k = slr.linear_params_from_slr(mean_k, cov_k, meas_bar, psi, phi)

        # measurements are zero indexed, i.e. meas[k-1] --> y_k
        meas_diff_k = measurements[k, :] - meas_bar
        _cost += meas_diff_k.T @ np.linalg.inv(meas_model.meas_noise(k) + Lambda_k) @ meas_diff_k

    return _cost


def slr_noop_cost(means, covs):
    return None
