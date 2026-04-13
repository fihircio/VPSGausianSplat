import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import faiss
import numpy as np
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.feature_set import FeatureSet
from backend.models.frame import Frame
from backend.models.scene import Scene
from backend.utils.config import get_settings


@dataclass
class FrameFeatureData:
    keypoints_xy: np.ndarray
    descriptors: np.ndarray
    point3d_ids: np.ndarray
    points3d_xyz: np.ndarray


class FeatureService:
    COLMAP_ASSOCIATION_MAX_PX = 6.0

    @staticmethod
    def build_scene_feature_index(scene: Scene, db: Session) -> FeatureSet:
        feature_dir = FeatureService._scene_feature_dir(scene.id)
        per_frame_dir = feature_dir / "frames"
        per_frame_dir.mkdir(parents=True, exist_ok=True)

        points3d_by_id = FeatureService._parse_points3d(Path(scene.sparse_dir) / "sparse_txt" / "points3D.txt")
        observations_by_image = FeatureService._parse_image_observations(
            Path(scene.sparse_dir) / "sparse_txt" / "images.txt"
        )

        frames = db.scalars(
            select(Frame).where(Frame.scene_id == scene.id).order_by(Frame.frame_index.asc())
        ).all()
        if not frames:
            raise RuntimeError("No frames found for scene")

        global_descriptors: list[np.ndarray] = []
        global_points3d: list[np.ndarray] = []
        global_point_ids: list[np.ndarray] = []
        global_frame_ids: list[np.ndarray] = []

        for frame in frames:
            frame_features = FeatureService.extract_and_save_frame_features(
                frame=frame,
                output_path=per_frame_dir / f"frame_{frame.frame_index:06d}.npz",
                image_observations=observations_by_image.get(Path(frame.image_path).name, []),
                points3d_by_id=points3d_by_id,
            )
            valid = frame_features.point3d_ids >= 0
            if not np.any(valid):
                continue
            global_descriptors.append(frame_features.descriptors[valid].astype(np.float32))
            global_points3d.append(frame_features.points3d_xyz[valid].astype(np.float32))
            global_point_ids.append(frame_features.point3d_ids[valid].astype(np.int64))
            global_frame_ids.append(np.full(int(np.sum(valid)), frame.id, dtype=np.int64))

        if not global_descriptors:
            raise RuntimeError("No ORB descriptors could be associated with COLMAP 3D points.")

        descriptors = np.concatenate(global_descriptors, axis=0).astype(np.float32)
        points3d = np.concatenate(global_points3d, axis=0).astype(np.float32)
        point_ids = np.concatenate(global_point_ids, axis=0).astype(np.int64)
        frame_ids = np.concatenate(global_frame_ids, axis=0).astype(np.int64)

        index_path = feature_dir / "orb.faiss"
        metadata_path = feature_dir / "scene_features.npz"
        stats_path = feature_dir / "stats.json"

        index = faiss.IndexFlatL2(descriptors.shape[1])
        index.add(descriptors)
        faiss.write_index(index, str(index_path))
        np.savez_compressed(
            str(metadata_path),
            points3d=points3d,
            point3d_ids=point_ids,
            frame_ids=frame_ids,
        )

        with stats_path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "scene_id": scene.id,
                    "num_indexed_descriptors": int(descriptors.shape[0]),
                    "num_unique_points3d": int(np.unique(point_ids).shape[0]),
                    "num_frames": len(frames),
                },
                f,
                indent=2,
            )

        feature_set = db.scalar(
            select(FeatureSet).where(FeatureSet.scene_id == scene.id).order_by(desc(FeatureSet.id))
        )
        if feature_set is None:
            feature_set = FeatureSet(scene_id=scene.id, index_path="", metadata_path="", num_descriptors=0)

        feature_set.index_path = str(index_path.resolve())
        feature_set.metadata_path = str(metadata_path.resolve())
        feature_set.num_descriptors = int(descriptors.shape[0])
        db.add(feature_set)

        scene.faiss_index_path = feature_set.index_path
        scene.feature_meta_path = feature_set.metadata_path
        db.add(scene)
        db.commit()
        db.refresh(feature_set)
        return feature_set

    @staticmethod
    def extract_and_save_frame_features(
        frame: Frame,
        output_path: Path,
        image_observations: list[dict],
        points3d_by_id: dict[int, np.ndarray],
    ) -> FrameFeatureData:
        keypoints_xy, descriptors = FeatureService.extract_orb(Path(frame.image_path))
        point3d_ids = np.full(keypoints_xy.shape[0], -1, dtype=np.int64)
        points3d_xyz = np.zeros((keypoints_xy.shape[0], 3), dtype=np.float32)

        observation_points = np.array(
            [obs["xy"] for obs in image_observations if obs["point3d_id"] in points3d_by_id],
            dtype=np.float32,
        )
        observation_ids = np.array(
            [obs["point3d_id"] for obs in image_observations if obs["point3d_id"] in points3d_by_id],
            dtype=np.int64,
        )

        if observation_points.size > 0 and keypoints_xy.size > 0:
            deltas = keypoints_xy[:, None, :] - observation_points[None, :, :]
            distances = np.linalg.norm(deltas, axis=2)
            nearest_idx = np.argmin(distances, axis=1)
            nearest_dist = distances[np.arange(distances.shape[0]), nearest_idx]
            valid = nearest_dist <= FeatureService.COLMAP_ASSOCIATION_MAX_PX
            point3d_ids[valid] = observation_ids[nearest_idx[valid]]
            if np.any(valid):
                points3d_xyz[valid] = np.stack(
                    [points3d_by_id[int(pid)] for pid in point3d_ids[valid]],
                    axis=0,
                ).astype(np.float32)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            str(output_path),
            keypoints_xy=keypoints_xy.astype(np.float32),
            descriptors=descriptors.astype(np.uint8),
            point3d_ids=point3d_ids,
            points3d_xyz=points3d_xyz.astype(np.float32),
        )
        return FrameFeatureData(
            keypoints_xy=keypoints_xy.astype(np.float32),
            descriptors=descriptors.astype(np.uint8),
            point3d_ids=point3d_ids,
            points3d_xyz=points3d_xyz.astype(np.float32),
        )

    @staticmethod
    def extract_orb(image_path: Path) -> tuple[np.ndarray, np.ndarray]:
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

    @staticmethod
    def _parse_points3d(points_txt: Path) -> dict[int, np.ndarray]:
        points: dict[int, np.ndarray] = {}
        with points_txt.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                point_id = int(parts[0])
                points[point_id] = np.array(
                    [float(parts[1]), float(parts[2]), float(parts[3])],
                    dtype=np.float32,
                )
        return points

    @staticmethod
    def _parse_image_observations(images_txt: Path) -> dict[str, list[dict]]:
        observations: dict[str, list[dict]] = {}
        with images_txt.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        for idx in range(0, len(lines), 2):
            header = lines[idx].split()
            image_name = header[9]
            points_line = lines[idx + 1].split()
            image_obs: list[dict] = []
            for j in range(0, len(points_line), 3):
                x = float(points_line[j])
                y = float(points_line[j + 1])
                point3d_id = int(float(points_line[j + 2]))
                image_obs.append({"xy": [x, y], "point3d_id": point3d_id})
            observations[image_name] = image_obs
        return observations
