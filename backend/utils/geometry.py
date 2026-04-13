import math

import cv2
import numpy as np


def qvec_to_rotmat(qvec: list[float]) -> np.ndarray:
    qw, qx, qy, qz = qvec
    return np.array(
        [
            [1 - 2 * qy**2 - 2 * qz**2, 2 * qx * qy - 2 * qz * qw, 2 * qx * qz + 2 * qy * qw],
            [2 * qx * qy + 2 * qz * qw, 1 - 2 * qx**2 - 2 * qz**2, 2 * qy * qz - 2 * qx * qw],
            [2 * qx * qz - 2 * qy * qw, 2 * qy * qz + 2 * qx * qw, 1 - 2 * qx**2 - 2 * qy**2],
        ],
        dtype=np.float64,
    )


def rotmat_to_quaternion(R: np.ndarray) -> list[float]:
    q = np.empty((4,), dtype=np.float64)
    trace = np.trace(R)
    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1.0)
        q[0] = 0.25 / s
        q[1] = (R[2, 1] - R[1, 2]) * s
        q[2] = (R[0, 2] - R[2, 0]) * s
        q[3] = (R[1, 0] - R[0, 1]) * s
    else:
        if R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            s = 2.0 * math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
            q[0] = (R[2, 1] - R[1, 2]) / s
            q[1] = 0.25 * s
            q[2] = (R[0, 1] + R[1, 0]) / s
            q[3] = (R[0, 2] + R[2, 0]) / s
        elif R[1, 1] > R[2, 2]:
            s = 2.0 * math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
            q[0] = (R[0, 2] - R[2, 0]) / s
            q[1] = (R[0, 1] + R[1, 0]) / s
            q[2] = 0.25 * s
            q[3] = (R[1, 2] + R[2, 1]) / s
        else:
            s = 2.0 * math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
            q[0] = (R[1, 0] - R[0, 1]) / s
            q[1] = (R[0, 2] + R[2, 0]) / s
            q[2] = (R[1, 2] + R[2, 1]) / s
            q[3] = 0.25 * s
    norm = np.linalg.norm(q)
    if norm == 0:
        return [1.0, 0.0, 0.0, 0.0]
    q /= norm
    return [float(q[1]), float(q[2]), float(q[3]), float(q[0])]  # xyzw


def projection_from_pose(K: np.ndarray, R_cw: np.ndarray, t_cw: np.ndarray) -> np.ndarray:
    Rt = np.hstack([R_cw, t_cw.reshape(3, 1)])
    return K @ Rt


def solve_pnp_pose(
    object_points: np.ndarray,
    image_points: np.ndarray,
    camera_matrix: np.ndarray,
) -> tuple[bool, np.ndarray, np.ndarray, np.ndarray]:
    success, rvec, tvec, inliers = cv2.solvePnPRansac(
        object_points=object_points,
        image_points=image_points,
        cameraMatrix=camera_matrix,
        distCoeffs=None,
        iterationsCount=200,
        reprojectionError=8.0,
        confidence=0.99,
        flags=cv2.SOLVEPNP_EPNP,
    )
    return bool(success), rvec, tvec, inliers if inliers is not None else np.empty((0, 1), dtype=np.int32)
