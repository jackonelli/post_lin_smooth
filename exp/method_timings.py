"""Example: Levenberg-Marquardt regularised IEKS smoothing

Reproducing the experiment (with two different meas. models) in the paper:

"Levenberg-Marquardt and line-search extended Kalman smoother".

The problem is evaluated for
(Original experiment)
- (GN-)IEKS
- LM-IEKS
(Additional models)
- (GN-)IPLS
- Reg-IPLS (LM-IPLS)
"""

from enum import Enum
from timeit import timeit
from functools import partial
import logging
from pathlib import Path
from functools import partial
import numpy as np
import matplotlib.pyplot as plt
from src import visualization as vis
from src.filter.ekf import Ekf
from src.smoother.ext.eks import Eks
from src.smoother.ext.ieks import Ieks
from src.smoother.ext.lm_ieks import LmIeks
from src.smoother.ext.ls_ieks import LsIeks
from src.line_search import ArmijoLineSearch
from src.smoother.slr.ipls import SigmaPointIpls
from src.smoother.slr.lm_ipls import SigmaPointLmIpls
from src.smoother.slr.ls_ipls import SigmaPointLsIpls
from src.slr.sigma_points import SigmaPointSlr
from src.sigma_points import SphericalCubature
from src.cost_fn.slr import (
    slr_smoothing_cost_pre_comp,
    slr_smoothing_cost_means,
    slr_noop_cost,
    dir_der_slr_smoothing_cost,
)
from src.cost_fn.ext import analytical_smoothing_cost, dir_der_analytical_smoothing_cost, noop_cost
from src.utils import setup_logger
from src.analytics import rmse
from src.visualization import to_tikz, write_to_tikz_file
from src.models.range_bearing import MultiSensorRange, MultiSensorBearings
from src.models.coord_turn import CoordTurn
from data.lm_ieks_paper.coord_turn_example import Type, get_specific_states_from_file, simulate_data
from exp.coord_turn.common import run_smoothing, calc_iter_metrics, mc_stats


def main():
    log = logging.getLogger(__name__)
    experiment_name = "lm_ieks"
    setup_logger(f"logs/{experiment_name}.log", logging.WARNING)
    log.info(f"Running experiment: {experiment_name}")

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
    motion_model = CoordTurn(dt, Q)

    sens_pos_1 = np.array([-1.5, 0.5])
    sens_pos_2 = np.array([1, 1])
    sensors = np.row_stack((sens_pos_1, sens_pos_2))
    std = 0.5
    R = std ** 2 * np.eye(2)

    prior_mean = np.array([0, 0, 1, 0, 0])
    prior_cov = np.diag([0.1, 0.1, 1, 1, 1])

    num_iter = 1
    np.random.seed(0)
    states, all_meas, _, xs_ss = get_specific_states_from_file(Path.cwd() / "data/lm_ieks_paper", Type.LM, num_iter)
    K = all_meas.shape[0]
    covs = np.array([prior_cov] * K) * (0.90 + np.random.rand() / 5)

    meas_model = MultiSensorRange(sensors, R)
    measurements = all_meas[:, :2]

    cost_fn_eks = partial(
        analytical_smoothing_cost,
        measurements=measurements,
        m_1_0=prior_mean,
        P_1_0=prior_cov,
        motion_model=motion_model,
        meas_model=meas_model,
    )

    dir_der_eks = partial(
        dir_der_analytical_smoothing_cost,
        measurements=measurements,
        m_1_0=prior_mean,
        P_1_0=prior_cov,
        motion_model=motion_model,
        meas_model=meas_model,
    )

    sigma_point_method = SphericalCubature()

    cost_fn_ipls = partial(
        slr_smoothing_cost_pre_comp,
        measurements=measurements,
        m_1_0=prior_mean,
        P_1_0_inv=np.linalg.inv(prior_cov),
    )
    time_ieks = partial(
        Ieks(motion_model, meas_model, num_iter).filter_and_smooth_with_init_traj,
        measurements,
        prior_mean,
        prior_cov,
        (xs_ss, covs),
        1,
        noop_cost,
    )

    time_lm_ieks = partial(
        LmIeks(motion_model, meas_model, num_iter, 10, 1e-2, 10).filter_and_smooth_with_init_traj,
        measurements,
        prior_mean,
        prior_cov,
        (xs_ss, covs),
        1,
        cost_fn_eks,
    )

    time_ls_ieks = partial(
        LsIeks(
            motion_model,
            meas_model,
            num_iter,
            ArmijoLineSearch(cost_fn_eks, dir_der_eks, c_1=0.1),
        ).filter_and_smooth_with_init_traj,
        measurements,
        prior_mean,
        prior_cov,
        (xs_ss, covs),
        1,
        cost_fn_eks,
    )
    time_ipls = partial(
        SigmaPointIpls(motion_model, meas_model, sigma_point_method, num_iter).filter_and_smooth_with_init_traj,
        measurements,
        prior_mean,
        prior_cov,
        (xs_ss, covs),
        1,
        slr_noop_cost,
    )
    time_lm_ipls = partial(
        SigmaPointLmIpls(
            motion_model, meas_model, sigma_point_method, num_iter, cost_improv_iter_lim=10, lambda_=1e-2, nu=10
        ).filter_and_smooth_with_init_traj,
        measurements,
        prior_mean,
        prior_cov,
        (xs_ss, covs),
        1,
        cost_fn_ipls,
    )

    cost_fn_ls_ipls = partial(
        slr_smoothing_cost_means,
        measurements=measurements,
        m_1_0=prior_mean,
        P_1_0_inv=np.linalg.inv(prior_cov),
        motion_fn=motion_model.map_set,
        meas_fn=meas_model.map_set,
        slr_method=SigmaPointSlr(sigma_point_method),
    )
    time_ls_ipls = partial(
        SigmaPointLsIpls(
            motion_model, meas_model, sigma_point_method, num_iter, partial(ArmijoLineSearch, c_1=0.1), 10
        ).filter_and_smooth_with_init_traj,
        measurements,
        prior_mean,
        prior_cov,
        (xs_ss, covs),
        1,
        cost_fn_ls_ipls,
    )
    num_samples = 10
    time_ieks = timeit(time_ieks, number=num_samples) / (num_iter * num_samples)
    time_lm_ieks = timeit(time_lm_ieks, number=num_samples) / (num_iter * num_samples)
    time_ls_ieks = timeit(time_ls_ieks, number=num_samples) / (num_iter * num_samples)
    time_ipls = timeit(time_ipls, number=num_samples) / (num_iter * num_samples)
    time_lm_ipls = timeit(time_lm_ipls, number=num_samples) / (num_iter * num_samples)
    time_ls_ipls = timeit(time_ls_ipls, number=num_samples) / (num_iter * num_samples)
    print(f"IEKS: {time_ieks:.2f} s, 100.0%")
    print(f"LM-IEKS: {time_lm_ieks:.2f} s, {time_lm_ieks/time_ieks*100:.2f}%")
    print(f"LS-IEKS: {time_ls_ieks:.2f} s, {time_ls_ieks/time_ieks*100:.2f}%")
    print(f"IPLS: {time_ipls:.2f} s, {time_ipls/time_ieks*100:.2f}%")
    print(f"LM-IPLS: {time_lm_ipls:.2f} s, {time_lm_ipls/time_ieks*100:.2f}%")
    print(f"LS-IPLS: {time_ls_ipls:.2f} s, {time_ls_ipls/time_ieks*100:.2f}%")


# TODO: Sep module?
def plot_results(states, trajs_and_costs, meas, skip_cov=50):
    means_and_covs = [(ms, Ps, f"{label}-{len(cost)}") for (ms, Ps, cost, label) in trajs_and_costs]
    # costs = [
    #     (cost, f"{label}-{len(cost)}") for (_, _, cost, label) in trajs_and_costs
    # ]
    # _, (ax_1, ax_2) = plt.subplots(1, 2)
    fig, ax_1 = plt.subplots()
    vis.plot_2d_est(
        states,
        meas=meas,
        means_and_covs=means_and_covs,
        sigma_level=2,
        skip_cov=skip_cov,
        ax=ax_1,
    )
    plt.show()


def plot_cost(ax, costs):
    for (iter_cost, label) in costs:
        ax.semilogy(iter_cost, label=label)
    ax.set_xlabel("Iteration number i")
    ax.set_ylabel("$L_{LM}$")
    ax.set_title("Cost function")


class MeasType(Enum):
    Range = "range"
    Bearings = "bearings"


if __name__ == "__main__":
    main()
