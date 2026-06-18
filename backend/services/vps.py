import json
import logging
from pathlib import Path

import cv2
import faiss
import numpy as np
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.feature_set import FeatureSet
from backend.models.frame import Frame
from backend.models.scene import Scene
from backend.services.feature_service import FeatureService
from backend.services.features.feature_factory import FeatureFactory
from backend.utils.config import get_settings
from backend.utils.geometry import rotmat_to_quaternion, solve_pnp_pose
from backend.utils.storage import get_storage

logger = logging.getLogger(__name__)


class VPSService:
    MIN_INLIERS = 20

    @staticmethod
    def build_feature_db(scene: Scene, db: Session) -> FeatureSet:
        return FeatureService.build_scene_feature_index(scene, db)

    @staticmethod
    def localize(scene_id: str, query_image_path: Path, db: Session,
                 hint_position=None, hint_radius=25.0, hint_floor_height=None, geo_hint=None) -> dict:
        return VPSService.localize_image(
            scene_id=scene_id, query_image_path=query_image_path, db=db,
            hint_position=hint_position, hint_radius=hint_radius,
            hint_floor_height=hint_floor_height, geo_hint=geo_hint,
        )

    @staticmethod
    def localize_image(scene_id: str, query_image_path: str, db: Session,
                       hint_position=None, hint_radius=25.0, hint_floor_height=None, geo_hint=None) -> dict:
        scene = db.get(Scene, scene_id)
        if not scene:
            raise ValueError("Scene not found")

        # Get the primary feature set (usually ORB or DISK)
        feature_set = db.scalar(
            select(FeatureSet).where(FeatureSet.scene_id == scene_id).order_by(desc(FeatureSet.id))
        )
        if not feature_set:
            raise RuntimeError("No feature index built for scene")

        result = None
        error = None

        try:
            result = VPSService._localize_with_feature_set(
                scene_id, query_image_path, feature_set, db,
                hint_position=hint_position, hint_radius=hint_radius,
                hint_floor_height=hint_floor_height, geo_hint=geo_hint,
            )
        except Exception as e:
            error = e

        # Fallback logic: boost confidence or try SIFT if primary failed/low confidence
        CONFIDENCE_THRESHOLD = 0.25
        INLIER_THRESHOLD = 30

        needs_fallback = (
            result is None or 
            result.get("confidence", 0) < CONFIDENCE_THRESHOLD or 
            result.get("inliers", 0) < INLIER_THRESHOLD
        )

        if needs_fallback and feature_set.feature_mode.upper() != "SIFT":
            sift_set = db.scalar(
                select(FeatureSet)
                .where(FeatureSet.scene_id == scene_id, FeatureSet.feature_mode == "SIFT")
                .order_by(desc(FeatureSet.id))
            )
            if sift_set:
                try:
                    sift_result = VPSService._localize_with_feature_set(scene_id, query_image_path, sift_set, db)
                    # If SIFT is better, use it
                    if result is None or sift_result.get("confidence", 0) > result.get("confidence", 0):
                        result = sift_result
                        result["mode"] = "SIFT_FALLBACK"
                except Exception:
                    pass # If SIFT also fails, stick with primary error or result

        if result is None:
            raise error or RuntimeError("Localization failed")

        # Apply calibration if exists
        result = VPSService._apply_calibration(scene_id, result)
        
        return result

    @staticmethod
    def localize_multi(
        scene_id: str,
        query_image_paths: list[Path],
        db: Session,
        hint_position=None, hint_radius=25.0, hint_floor_height=None, geo_hint=None,
    ) -> dict:
        scene = db.get(Scene, scene_id)
        if not scene:
            raise ValueError("Scene not found")

        feature_set = db.scalar(
            select(FeatureSet).where(FeatureSet.scene_id == scene_id).order_by(desc(FeatureSet.id))
        )
        if not feature_set:
            raise RuntimeError("No feature index built for scene")

        storage = get_storage()
        local_index_path = storage.ensure_local_copy(feature_set.index_path)
        local_metadata_path = storage.ensure_local_copy(feature_set.metadata_path)

        extractor = FeatureFactory.get_extractor(feature_set.feature_mode)
        index = faiss.read_index(str(local_index_path))
        metadata = np.load(str(local_metadata_path))
        points3d = metadata["points3d"].astype(np.float32)
        point3d_ids = metadata["point3d_ids"].astype(np.int64)

        all_object_points = []
        all_image_points = []
        frame_match_counts = []
        frame_index_map = []

        for i, img_path in enumerate(query_image_paths):
            try:
                local_query_path = storage.ensure_local_copy(img_path)
                query_kp, query_desc = extractor.extract(local_query_path)
                if query_desc.shape[0] < 8:
                    frame_match_counts.append(0)
                    continue

                distances, indices = index.search(query_desc.astype(np.float32), 2)
                obj_pts, img_pts, count = VPSService._collect_correspondences(
                    query_keypoints_xy=query_kp,
                    distances=distances,
                    indices=indices,
                    points3d=points3d,
                    point3d_ids=point3d_ids,
                )
                if count >= 8:
                    all_object_points.append(obj_pts)
                    all_image_points.append(img_pts)
                    frame_index_map.extend([i] * len(obj_pts))
                frame_match_counts.append(count)
            except Exception as e:
                logger.warning(f"Multi-frame frame {i} failed: {e}")
                frame_match_counts.append(0)

        if not all_object_points:
            raise RuntimeError("No frame produced enough matches for multi-frame localization")

        combined_object_points = np.concatenate(all_object_points, axis=0).astype(np.float32)
        combined_image_points = np.concatenate(all_image_points, axis=0).astype(np.float32)
        frame_idx_arr = np.array(frame_index_map, dtype=np.int32)
        total_matches = len(combined_object_points)

        hint_used = None
        if hint_position is not None:
            pos = np.array(hint_position, dtype=np.float32)
            dists = np.linalg.norm(combined_object_points - pos, axis=1)
            valid = dists < hint_radius
            if valid.any():
                combined_object_points = combined_object_points[valid]
                combined_image_points = combined_image_points[valid]
                frame_idx_arr = frame_idx_arr[valid]
                total_matches = len(combined_object_points)
                hint_used = "hintPosition"

        if hint_floor_height is not None and total_matches >= 8:
            y_min, y_max = hint_floor_height
            valid = (combined_object_points[:, 1] >= y_min) & (combined_object_points[:, 1] <= y_max)
            if valid.any():
                combined_object_points = combined_object_points[valid]
                combined_image_points = combined_image_points[valid]
                frame_idx_arr = frame_idx_arr[valid]
                total_matches = len(combined_object_points)
                hint_used = "hintFloorHeight" if hint_used is None else f"{hint_used}+hintFloorHeight"

        if geo_hint is not None:
            logger.info(f"geo_hint received but no geo reference stored for scene {scene_id}, skipping")

        camera_matrix = VPSService._estimate_query_intrinsics(scene_id, db, query_image_paths[0])

        success, rvec, tvec, inliers = solve_pnp_pose(combined_object_points, combined_image_points, camera_matrix)
        inlier_count = int(len(inliers))
        confidence = float(inlier_count / max(total_matches, 1))

        if not success or inlier_count < VPSService.MIN_INLIERS:
            raise RuntimeError(
                f"Multi-frame localization rejected: {inlier_count} inliers from {total_matches} matches across {len([c for c in frame_match_counts if c >= 8])} frames"
            )

        inlier_mask = np.zeros(len(combined_object_points), dtype=bool)
        inlier_mask[list(inliers)] = True

        per_frame_inliers = {}
        for i in range(len(query_image_paths)):
            frame_mask = frame_idx_arr == i
            if frame_mask.any():
                per_frame_inliers[i] = int(inlier_mask[frame_mask].sum())

        frames_used = sum(1 for v in per_frame_inliers.values() if v >= 10)
        frame_confidences = []
        for i in range(len(query_image_paths)):
            count = frame_match_counts[i]
            inl = per_frame_inliers.get(i, 0)
            frame_confidences.append(float(inl / max(count, 1)) if count > 0 else 0.0)

        R_cw, _ = cv2.Rodrigues(rvec)
        R_wc = R_cw.T
        position = (-R_wc @ tvec).reshape(3)
        rotation = rotmat_to_quaternion(R_wc)

        result = {
            "position": [float(position[0]), float(position[1]), float(position[2])],
            "rotation": [float(rotation[0]), float(rotation[1]), float(rotation[2]), float(rotation[3])],
            "inliers": inlier_count,
            "confidence": confidence,
            "frames_used": frames_used,
            "frame_confidences": frame_confidences,
            "hint_used": hint_used,
        }

        result = VPSService._apply_calibration(scene_id, result)
        return result

    @staticmethod
    def _localize_with_feature_set(
        scene_id: str, query_image_path: str, feature_set: FeatureSet, db: Session,
        hint_position=None, hint_radius=25.0, hint_floor_height=None, geo_hint=None,
    ) -> dict:
        storage = get_storage()
        
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

        hint_used = None

        if hint_position is not None and total_matches >= 8:
            pos = np.array(hint_position, dtype=np.float32)
            dists = np.linalg.norm(object_points - pos, axis=1)
            valid = dists < hint_radius
            if valid.any():
                object_points = object_points[valid]
                image_points = image_points[valid]
                total_matches = len(object_points)
                hint_used = "hintPosition"
                logger.info(f"hintPosition filtered to {total_matches} matches within {hint_radius}m")

        if hint_floor_height is not None and total_matches >= 8:
            y_min, y_max = hint_floor_height
            valid = (object_points[:, 1] >= y_min) & (object_points[:, 1] <= y_max)
            if valid.any():
                object_points = object_points[valid]
                image_points = image_points[valid]
                total_matches = len(object_points)
                hint_used = "hintFloorHeight" if hint_used is None else f"{hint_used}+hintFloorHeight"
                logger.info(f"hintFloorHeight [{y_min}, {y_max}] filtered to {total_matches} matches")

        if geo_hint is not None:
            logger.info(f"geo_hint received but no geo reference stored for scene {scene_id}, skipping")

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
            "mode": feature_set.feature_mode,
            "hint_used": hint_used,
        }

    @staticmethod
    def _apply_calibration(scene_id: str, result: dict) -> dict:
        storage = get_storage()
        cal_path_remote = f"features/{scene_id}/calibration.json"
        
        try:
            local_cal_path = storage.ensure_local_copy(cal_path_remote)
            if not local_cal_path.exists():
                return result
                
            with open(local_cal_path, "r") as f:
                cal = json.load(f)
            
            # Calibration transform (similarity): P_global = s * R_global * P_local + t_global
            s = cal.get("scale", 1.0)
            R = np.array(cal.get("rotation_matrix", [[1,0,0],[0,1,0],[0,0,1]]))
            t = np.array(cal.get("translation", [0,0,0]))
            
            pos_local = np.array(result["position"])
            pos_global = s * (R @ pos_local) + t
            
            # Rotation alignment: R_global_cam = R_cal * R_local_cam
            # Result stores [x,y,z,w] from rotmat_to_quaternion
            # We need to convert back to matrix, multiply, and convert back to quat
            from backend.utils.geometry import qvec_to_rotmat
            # result["rotation"] is [x,y,z,w]. qvec_to_rotmat expects [w,x,y,z]
            q_local = result["rotation"]
            R_local = qvec_to_rotmat([q_local[3], q_local[0], q_local[1], q_local[2]])
            R_global = R @ R_local
            q_global = rotmat_to_quaternion(R_global)
            
            result["position"] = pos_global.tolist()
            result["rotation"] = q_global
            result["calibrated"] = True
            
        except Exception as e:
            print(f"Failed to apply calibration: {e}")
            
        return result

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
