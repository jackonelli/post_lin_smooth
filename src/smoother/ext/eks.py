"""Extended Kalman Smoother (EKS)
Also known as the Extended Rauch-Tung-Striebel Smoother (ERTSS)
"""
from src.smoother.base import Smoother
from src.models.affine import AffineModel
from src.filter.ekf import Ekf, ext_lin


class Eks(Smoother):
    def __init__(self, motion_model: AffineModel, meas_model: AffineModel):
        super().__init__()
        self._motion_model = motion_model
        self._meas_model = meas_model

    def _motion_lin(self, mean, _cov, time_step):
        F, b = ext_lin(self._motion_model, mean, time_step)
        return (F, b, 0)

    def _meas_lin(self, mean, _cov, time_step):
        H, c = ext_lin(self._meas_model, mean, time_step)
        return (H, c, 0)

    def _filter_seq(self, measurements, m_1_0, P_1_0):
        return Ekf(self._motion_model, self._meas_model).filter_seq(measurements, m_1_0, P_1_0)
