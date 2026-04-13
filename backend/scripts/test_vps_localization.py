import argparse
import json
import math
from pathlib import Path

import numpy as np
from sqlalchemy import select

from backend.models.frame import Frame
from backend.utils.db import SessionLocal
from backend.utils.geometry import rotmat_to_quaternion
from backend.services.vps import VPSService


def quaternion_angle_deg(q1_xyzw: list[float], q2_xyzw: list[float]) -> float:
    q1 = np.array(q1_xyzw, dtype=np.float64)
    q2 = np.array(q2_xyzw, dtype=np.float64)
    q1 /= np.linalg.norm(q1)
    q2 /= np.linalg.norm(q2)
    dot = float(np.clip(np.abs(np.dot(q1, q2)), -1.0, 1.0))
    return math.degrees(2.0 * math.acos(dot))


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate VPS localization against a known scene frame.")
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--frame-index", type=int, default=0)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        frame = db.scalar(
            select(Frame)
            .where(Frame.scene_id == args.scene_id, Frame.frame_index == args.frame_index)
        )
        if frame is None:
            raise SystemExit(f"Frame not found for scene={args.scene_id} frame_index={args.frame_index}")
        if not frame.pose_json:
            raise SystemExit("Selected frame does not have ground-truth COLMAP pose")

        result = VPSService.localize_image(
            scene_id=args.scene_id,
            query_image_path=Path(frame.image_path),
            db=db,
        )

        gt_position = np.array(frame.pose_json["position_wc"], dtype=np.float64)
        gt_rotation = rotmat_to_quaternion(np.array(frame.pose_json["rotation_wc"], dtype=np.float64))
        est_position = np.array(result["position"], dtype=np.float64)
        est_rotation = result["rotation"]

        translation_error = float(np.linalg.norm(est_position - gt_position))
        rotation_error_deg = quaternion_angle_deg(est_rotation, gt_rotation)

        output = {
            "scene_id": args.scene_id,
            "frame_index": args.frame_index,
            "query_image_path": frame.image_path,
            "estimated_pose": result,
            "ground_truth": {
                "position": gt_position.tolist(),
                "rotation": gt_rotation,
            },
            "translation_error": translation_error,
            "rotation_error_deg": rotation_error_deg,
        }
        print(json.dumps(output, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
