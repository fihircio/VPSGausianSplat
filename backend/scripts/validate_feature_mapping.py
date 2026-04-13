import argparse
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import select

from backend.models.frame import Frame
from backend.models.scene import Scene
from backend.services.feature_mapper import FeatureMapper
from backend.utils.db import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate ORB-to-3D feature mapping on a training image.")
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--frame-index", type=int, default=0)
    parser.add_argument("--ratio", type=float, default=0.85)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        scene = db.get(Scene, args.scene_id)
        if scene is None:
            raise SystemExit(f"Scene not found: {args.scene_id}")
        frame = db.scalar(
            select(Frame).where(Frame.scene_id == args.scene_id, Frame.frame_index == args.frame_index)
        )
        if frame is None:
            raise SystemExit(f"Frame not found: scene={args.scene_id}, frame_index={args.frame_index}")

        feature_dir = Path(scene.feature_meta_path).parent if scene.feature_meta_path else None
        if feature_dir is None:
            raise SystemExit("Scene feature database not found. Run scene processing first.")

        scene_db_path = feature_dir / "scene_feature_db.npz"
        if not scene_db_path.exists():
            raise SystemExit(f"Mapping DB missing: {scene_db_path}")

        mapping = np.load(scene_db_path)
        db_descriptors = mapping["descriptors"].astype(np.uint8)
        db_points3d = mapping["points3d"].astype(np.float32)

        keypoints_xy, query_desc = FeatureMapper.extract_orb_features(Path(frame.image_path))
        if query_desc.shape[0] == 0:
            raise SystemExit("No ORB features found in query/training frame")
        if db_descriptors.shape[0] == 0:
            raise SystemExit("No descriptors in scene mapping DB")

        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        knn = matcher.knnMatch(query_desc, db_descriptors, k=2)

        valid = []
        for pair in knn:
            if len(pair) < 2:
                continue
            m, n = pair
            if m.distance < args.ratio * n.distance:
                valid.append(m)

        if not valid:
            print("Valid correspondences: 0")
            print("Unique 3D points: 0")
            print("Total query ORB keypoints: {}".format(query_desc.shape[0]))
            return

        pts2d = np.array([keypoints_xy[m.queryIdx] for m in valid], dtype=np.float32)
        pts3d = np.array([db_points3d[m.trainIdx] for m in valid], dtype=np.float32)
        unique_points = np.unique(pts3d, axis=0)

        print(f"Scene: {args.scene_id}")
        print(f"Frame index: {args.frame_index}")
        print(f"Total query ORB keypoints: {query_desc.shape[0]}")
        print(f"Valid correspondences: {len(valid)}")
        print(f"Unique 3D points: {unique_points.shape[0]}")
        print(f"Mean descriptor distance: {np.mean([m.distance for m in valid]):.2f}")
        print(f"2D sample shape: {pts2d.shape}, 3D sample shape: {pts3d.shape}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
