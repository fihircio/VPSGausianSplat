from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.frame import Frame
from backend.models.scene import Scene
from backend.services.colmap_loader import ColmapImage, ColmapLoader, ColmapPoint3D
from backend.utils.config import get_settings


@dataclass
class SceneFeatureMapping:
    descriptors_uint8: np.ndarray
    points3d_xyz: np.ndarray
    point3d_ids: np.ndarray
    frame_ids: np.ndarray
    total_orb_features: int
    total_mapped_features: int


class FeatureMapper:
    PIXEL_DISTANCE_THRESHOLD = 6.0

    @staticmethod
    def build_scene_mapping(scene: Scene, db: Session) -> tuple[SceneFeatureMapping, Path]:
        feature_dir = FeatureMapper._scene_feature_dir(scene.id)
        frames_dir = feature_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        sparse_model_dir = Path(scene.sparse_dir) / "sparse" / "0"
        images_by_name, points3d_by_id = ColmapLoader.load_sparse_model(sparse_model_dir)

        frames = db.scalars(select(Frame).where(Frame.scene_id == scene.id).order_by(Frame.frame_index.asc())).all()
        if not frames:
            raise RuntimeError("No frames available for scene feature mapping")

        global_desc: list[np.ndarray] = []
        global_xyz: list[np.ndarray] = []
        global_point_ids: list[np.ndarray] = []
        global_frame_ids: list[np.ndarray] = []
        mapped_counts: dict[str, int] = {}
        total_orb = 0
        total_mapped = 0

        for frame in frames:
            image_name = Path(frame.image_path).name
            colmap_image = images_by_name.get(image_name)
            if colmap_image is None:
                mapped_counts[image_name] = 0
                continue
            frame_mapping = FeatureMapper._build_frame_mapping(
                image_path=Path(frame.image_path),
                colmap_image=colmap_image,
                points3d_by_id=points3d_by_id,
            )
            frame_out = frames_dir / f"frame_{frame.frame_index:06d}.npz"
            np.savez_compressed(
                str(frame_out),
                keypoints_xy=frame_mapping["keypoints_xy"],
                descriptors=frame_mapping["descriptors_uint8"],
                mapped_point3d_ids=frame_mapping["mapped_point3d_ids"],
                mapped_points3d_xyz=frame_mapping["mapped_points3d_xyz"],
            )

            valid = frame_mapping["mapped_point3d_ids"] >= 0
            mapped_count = int(np.sum(valid))
            mapped_counts[image_name] = mapped_count
            total_orb += int(frame_mapping["descriptors_uint8"].shape[0])
            total_mapped += mapped_count

            if mapped_count == 0:
                continue
            global_desc.append(frame_mapping["descriptors_uint8"][valid])
            global_xyz.append(frame_mapping["mapped_points3d_xyz"][valid])
            global_point_ids.append(frame_mapping["mapped_point3d_ids"][valid])
            global_frame_ids.append(np.full(mapped_count, frame.id, dtype=np.int64))

        if not global_desc:
            raise RuntimeError("No descriptor-to-3D mappings generated for this scene")

        descriptors_uint8 = np.concatenate(global_desc, axis=0).astype(np.uint8)
        points3d_xyz = np.concatenate(global_xyz, axis=0).astype(np.float32)
        point3d_ids = np.concatenate(global_point_ids, axis=0).astype(np.int64)
        frame_ids = np.concatenate(global_frame_ids, axis=0).astype(np.int64)

        scene_db_path = feature_dir / "scene_feature_db.npz"
        np.savez_compressed(
            str(scene_db_path),
            descriptors=descriptors_uint8,
            points3d=points3d_xyz,
            point3d_ids=point3d_ids,
            frame_ids=frame_ids,
        )

        with (feature_dir / "mapping_stats.json").open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "scene_id": scene.id,
                    "pixel_distance_threshold": FeatureMapper.PIXEL_DISTANCE_THRESHOLD,
                    "total_orb_features": total_orb,
                    "total_mapped_features": total_mapped,
                    "mapped_per_image": mapped_counts,
                },
                f,
                indent=2,
            )

        mapping = SceneFeatureMapping(
            descriptors_uint8=descriptors_uint8,
            points3d_xyz=points3d_xyz,
            point3d_ids=point3d_ids,
            frame_ids=frame_ids,
            total_orb_features=total_orb,
            total_mapped_features=total_mapped,
        )
        return mapping, scene_db_path

    @staticmethod
    def _build_frame_mapping(
        image_path: Path,
        colmap_image: ColmapImage,
        points3d_by_id: dict[int, ColmapPoint3D],
    ) -> dict[str, np.ndarray]:
        keypoints_xy, descriptors = FeatureMapper.extract_orb_features(image_path)
        mapped_point_ids = np.full(keypoints_xy.shape[0], -1, dtype=np.int64)
        mapped_points_xyz = np.zeros((keypoints_xy.shape[0], 3), dtype=np.float32)
        if keypoints_xy.shape[0] == 0:
            return {
                "keypoints_xy": keypoints_xy,
                "descriptors_uint8": descriptors,
                "mapped_point3d_ids": mapped_point_ids,
                "mapped_points3d_xyz": mapped_points_xyz,
            }

        valid_obs_mask = colmap_image.point3d_ids >= 0
        obs_xys = colmap_image.xys[valid_obs_mask]
        obs_point_ids = colmap_image.point3d_ids[valid_obs_mask]
        keep = np.array([pid in points3d_by_id for pid in obs_point_ids], dtype=bool)
        obs_xys = obs_xys[keep]
        obs_point_ids = obs_point_ids[keep]
        if obs_xys.shape[0] == 0:
            return {
                "keypoints_xy": keypoints_xy,
                "descriptors_uint8": descriptors,
                "mapped_point3d_ids": mapped_point_ids,
                "mapped_points3d_xyz": mapped_points_xyz,
            }

        deltas = keypoints_xy[:, None, :] - obs_xys[None, :, :]
        dists = np.linalg.norm(deltas, axis=2)
        nearest_orb_idx = np.argmin(dists, axis=0)
        nearest_dist = dists[nearest_orb_idx, np.arange(dists.shape[1])]

        # One ORB keypoint may be nearest for multiple COLMAP observations.
        # Keep only the closest observation per ORB keypoint.
        best_for_orb: dict[int, tuple[float, int]] = {}
        for obs_idx, orb_idx in enumerate(nearest_orb_idx):
            dist = float(nearest_dist[obs_idx])
            if dist > FeatureMapper.PIXEL_DISTANCE_THRESHOLD:
                continue
            point_id = int(obs_point_ids[obs_idx])
            current = best_for_orb.get(int(orb_idx))
            if current is None or dist < current[0]:
                best_for_orb[int(orb_idx)] = (dist, point_id)

        for orb_idx, (_, point_id) in best_for_orb.items():
            mapped_point_ids[orb_idx] = point_id
            mapped_points_xyz[orb_idx] = points3d_by_id[point_id].xyz

        return {
            "keypoints_xy": keypoints_xy,
            "descriptors_uint8": descriptors,
            "mapped_point3d_ids": mapped_point_ids,
            "mapped_points3d_xyz": mapped_points_xyz,
        }

    @staticmethod
    def extract_orb_features(image_path: Path) -> tuple[np.ndarray, np.ndarray]:
        settings = get_settings()
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise RuntimeError(f"Unable to read image: {image_path}")
        orb = cv2.ORB_create(nfeatures=settings.orb_nfeatures)
        keypoints, descriptors = orb.detectAndCompute(image, None)
        if descriptors is None or not keypoints:
            return np.empty((0, 2), dtype=np.float32), np.empty((0, 32), dtype=np.uint8)
        keypoints_xy = np.array([kp.pt for kp in keypoints], dtype=np.float32)
        return keypoints_xy, descriptors.astype(np.uint8)

    @staticmethod
    def _scene_feature_dir(scene_id: str) -> Path:
        settings = get_settings()
        feature_dir = settings.storage_root / "features" / scene_id
        feature_dir.mkdir(parents=True, exist_ok=True)
        return feature_dir
