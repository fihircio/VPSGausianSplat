import argparse
import json
import os
from pathlib import Path

import numpy as np

def compute_similarity_transform(P, Q):
    """
    Computes the similarity transform (s, R, t) such that Q = s * R * P + t
    P: (N, 3) matrix of local points
    Q: (N, 3) matrix of global points
    """
    if P.shape != Q.shape:
        raise ValueError("Matrix dimensions must match")

    n = P.shape[0]
    if n < 3:
        raise ValueError("At least 3 points are required for 7-DOF calibration")

    # 1. Centering
    mu_p = np.mean(P, axis=0)
    mu_q = np.mean(Q, axis=0)
    P_centered = P - mu_p
    Q_centered = Q - mu_q

    # 2. Covariance matrix
    H = P_centered.T @ Q_centered

    # 3. SVD for rotation
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T

    # Special case: handle reflection
    if np.linalg.det(R) < 0:
        Vt[2, :] *= -1
        R = Vt.T @ U.T

    # 4. Compute Scale
    dist_p = np.sum(np.linalg.norm(P_centered, axis=1))
    dist_q = np.sum(np.linalg.norm(Q_centered, axis=1))
    scale = dist_q / dist_p if dist_p > 0 else 1.0

    # 5. Compute Translation
    translation = mu_q - scale * (R @ mu_p)

    return scale, R, translation

def main():
    parser = argparse.ArgumentParser(description="Calibrate a scene space to global coordinates")
    parser.add_argument("--scene-id", required=True, help="UUID of the scene")
    parser.add_argument("--points", required=True, help="JSON file or string containing point pairs: [[local_xyz, global_xyz], ...]")
    parser.add_argument("--output", help="Custom output path for calibration.json")

    args = parser.parse_args()

    try:
        if os.path.exists(args.points):
            with open(args.points, "r") as f:
                point_data = json.load(f)
        else:
            point_data = json.loads(args.points)
    except Exception as e:
        print(f"Error parsing points: {e}")
        return

    P = np.array([pair[0] for pair in point_data])
    Q = np.array([pair[1] for pair in point_data])

    print(f"Calculating transform for {len(P)} points...")
    
    try:
        scale, R, t = compute_similarity_transform(P, Q)
    except Exception as e:
        print(f"Calibration failed: {e}")
        return

    calibration = {
        "scene_id": args.scene_id,
        "scale": float(scale),
        "rotation_matrix": R.tolist(),
        "translation": t.tolist(),
        "rmse": float(np.sqrt(np.mean(np.linalg.norm(Q - (scale * (P @ R.T) + t), axis=1)**2)))
    }

    print("\nCalibration Results:")
    print(f"  Scale Factor: {scale:.6f}")
    print(f"  RMSE Error:   {calibration['rmse']:.6f}")
    print(f"  Translation:  {t}")

    # Save to features directory
    from backend.utils.config import get_settings
    settings = get_settings()
    out_dir = Path(args.output) if args.output else settings.storage_root / "features" / args.scene_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "calibration.json"

    with open(out_path, "w") as f:
        json.dump(calibration, f, indent=2)

    print(f"\nSaved calibration to: {out_path}")

if __name__ == "__main__":
    main()
