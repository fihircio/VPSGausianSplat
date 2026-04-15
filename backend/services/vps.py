from pathlib import Path

import cv2
import faiss
import numpy as np
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.feature_set import FeatureSet
from backend.models.frame import Frame
from backend.models.scene import Scene
from backend.services.features.feature_factory import FeatureFactory
from backend.utils.config import get_settings
from backend.utils.geometry import rotmat_to_quaternion, solve_pnp_pose
from backend.utils.storage import get_storage


class VPSService:
    MIN_INLIERS = 20

    @staticmethod
    def build_feature_db(scene: Scene, db: Session) -> FeatureSet:
        return FeatureService.build_scene_feature_index(scene, db)

    @staticmethod
    def localize(scene_id: str, query_image_path: Path, db: Session) -> dict:
        return VPSService.localize_image(scene_id=scene_id, query_image_path=query_image_path, db=db)

    @staticmethod
    def localize_image(scene_id: str, query_image_path: str, db: Session) -> dict:
        storage = get_storage()
        scene = db.get(Scene, scene_id)
        if not scene:
            raise ValueError("Scene not found")

        feature_set = db.scalar(
            select(FeatureSet).where(FeatureSet.scene_id == scene_id).order_by(desc(FeatureSet.id))
        )
        if not feature_set:
            raise RuntimeError("Feature index not built for scene")

        # Ensure local copies of index and metadata
        local_index_path = storage.ensure_local_copy(feature_set.index_path)
        local_metadata_path = storage.ensure_local_copy(feature_set.metadata_path)
        local_query_path = storage.ensure_local_copy(query_image_path)

        extractor = FeatureFactory.get_extractor(feature_set.feature_mode)
        query_keypoints_xy, query_descriptors = extractor.extract(local_query_path)
        if query_descriptors.shape[0] < 8:
            raise RuntimeError(f"Not enough {feature_set.feature_mode} features in query image")

        index = faiss.read_index(str(local_index_path))
        metadata = np.load(str(local_metadata_path))
        points3d = metadata["points3d"].astype(np.float32)
        point3d_ids = metadata["point3d_ids"].astype(np.int64)

        distances, indices = index.search(query_descriptors.astype(np.float32), 2)
        object_points, image_points, total_matches = VPSService._collect_correspondences(
            query_keypoints_xy=query_keypoints_xy,
            distances=distances,
            indices=indices,
            points3d=points3d,
            point3d_ids=point3d_ids,
        )

        if total_matches < 8:
            raise RuntimeError("Insufficient descriptor matches after ratio test")

        camera_matrix = VPSService._estimate_query_intrinsics(scene_id=scene_id, db=db, query_image_path=query_image_path)
        success, rvec, tvec, inliers = solve_pnp_pose(object_points, image_points, camera_matrix)
        inlier_count = int(len(inliers))
        confidence = float(inlier_count / max(total_matches, 1))
        if not success or inlier_count < VPSService.MIN_INLIERS:
            raise RuntimeError(
                f"Localization rejected: {inlier_count} inliers from {total_matches} matches"
            )

        R_cw, _ = cv2.Rodrigues(rvec)
        R_wc = R_cw.T
        position = (-R_wc @ tvec).reshape(3)
        rotation = rotmat_to_quaternion(R_wc)

        return {
            "position": [float(position[0]), float(position[1]), float(position[2])],
            "rotation": [float(rotation[0]), float(rotation[1]), float(rotation[2]), float(rotation[3])],
            "inliers": inlier_count,
            "confidence": confidence,
        }

    @staticmethod
    def _collect_correspondences(
        query_keypoints_xy: np.ndarray,
        distances: np.ndarray,
        indices: np.ndarray,
        points3d: np.ndarray,
        point3d_ids: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, int]:
        best_by_point: dict[int, tuple[float, np.ndarray, np.ndarray]] = {}
        for query_idx, neighbor_ids in enumerate(indices):
            primary_idx = int(neighbor_ids[0])
            if primary_idx < 0:
                continue
            d1 = float(distances[query_idx, 0])
            d2 = float(distances[query_idx, 1]) if distances.shape[1] > 1 else float("inf")
            if not np.isfinite(d1) or d1 >= 0.85 * d2:
                continue
            point_id = int(point3d_ids[primary_idx])
            candidate = (
                d1,
                points3d[primary_idx].astype(np.float32),
                query_keypoints_xy[query_idx].astype(np.float32),
            )
            current = best_by_point.get(point_id)
            if current is None or d1 < current[0]:
                best_by_point[point_id] = candidate

        if not best_by_point:
            return (
                np.empty((0, 3), dtype=np.float32),
                np.empty((0, 2), dtype=np.float32),
                0,
            )

        object_points = np.stack([item[1] for item in best_by_point.values()], axis=0).astype(np.float32)
        image_points = np.stack([item[2] for item in best_by_point.values()], axis=0).astype(np.float32)
        return object_points, image_points, len(best_by_point)

    @staticmethod
    def _estimate_query_intrinsics(scene_id: str, db: Session, query_image_path: Path) -> np.ndarray:
        frame = db.scalar(
            select(Frame)
            .where(Frame.scene_id == scene_id, Frame.intrinsics_json.is_not(None))
            .order_by(Frame.frame_index.asc())
        )
        if not frame:
            raise RuntimeError("No reference intrinsics available for scene")

        intrinsics = frame.intrinsics_json
        fx = float(intrinsics["fx"])
        fy = float(intrinsics["fy"])
        cx = float(intrinsics["cx"])
        cy = float(intrinsics["cy"])
        ref_width = float(intrinsics.get("width", 0) or 0)
        ref_height = float(intrinsics.get("height", 0) or 0)

        storage = get_storage()
        local_query_path = storage.ensure_local_copy(str(query_image_path))
        
        image = cv2.imread(str(local_query_path), cv2.IMREAD_GRAYSCALE)
        query_height, query_width = image.shape[:2]

        if ref_width > 0 and ref_height > 0:
            scale_x = query_width / ref_width
            scale_y = query_height / ref_height
            fx *= scale_x
            fy *= scale_y
            cx *= scale_x
            cy *= scale_y

        return np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
