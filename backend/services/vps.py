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
from backend.utils.geometry import projection_from_pose, rotmat_to_quaternion, solve_pnp_pose


class VPSService:
    @staticmethod
    def build_feature_db(scene: Scene, db: Session) -> FeatureSet:
        settings = get_settings()
        feature_dir = settings.storage_root / "features" / scene.id
        feature_dir.mkdir(parents=True, exist_ok=True)
        index_path = feature_dir / "orb.index"
        metadata_path = feature_dir / "landmarks.npz"

        orb = cv2.ORB_create(nfeatures=settings.orb_nfeatures)
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        frames = db.scalars(
            select(Frame).where(Frame.scene_id == scene.id).order_by(Frame.frame_index.asc())
        ).all()
        valid_frames = [f for f in frames if f.pose_json and f.intrinsics_json]
        if len(valid_frames) < 2:
            raise RuntimeError("Need at least 2 frames with valid COLMAP poses for VPS feature DB.")

        descriptor_rows: list[np.ndarray] = []
        landmark_rows: list[np.ndarray] = []

        for idx in range(len(valid_frames) - 1):
            f1 = valid_frames[idx]
            f2 = valid_frames[idx + 1]
            data1 = VPSService._extract_frame_features(Path(f1.image_path), orb)
            data2 = VPSService._extract_frame_features(Path(f2.image_path), orb)
            if data1 is None or data2 is None:
                continue
            kp1, des1 = data1
            kp2, des2 = data2
            matches = bf.match(des1, des2)
            if len(matches) < 8:
                continue
            matches = sorted(matches, key=lambda m: m.distance)[:300]

            K1 = VPSService._k_from_intrinsics(f1.intrinsics_json)
            K2 = VPSService._k_from_intrinsics(f2.intrinsics_json)
            R1, t1 = VPSService._rt_from_pose(f1.pose_json)
            R2, t2 = VPSService._rt_from_pose(f2.pose_json)
            P1 = projection_from_pose(K1, R1, t1)
            P2 = projection_from_pose(K2, R2, t2)

            pts1 = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 2)
            pts2 = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 2)
            pts4d = cv2.triangulatePoints(P1, P2, pts1.T, pts2.T).T
            w = pts4d[:, 3:4]
            w[np.abs(w) < 1e-8] = 1e-8
            pts3d = pts4d[:, :3] / w

            z1 = (R1 @ pts3d.T + t1.reshape(3, 1))[2, :]
            z2 = (R2 @ pts3d.T + t2.reshape(3, 1))[2, :]
            valid = (z1 > 0) & (z2 > 0) & np.all(np.isfinite(pts3d), axis=1)

            for j, match in enumerate(matches):
                if not valid[j]:
                    continue
                descriptor_rows.append(des1[match.queryIdx].astype(np.float32))
                landmark_rows.append(pts3d[j].astype(np.float32))

        if len(descriptor_rows) < 20:
            raise RuntimeError("Insufficient landmarks/descriptors generated for VPS indexing.")

        descriptors = np.stack(descriptor_rows, axis=0).astype(np.float32)
        landmarks = np.stack(landmark_rows, axis=0).astype(np.float32)
        index = faiss.IndexFlatL2(descriptors.shape[1])
        index.add(descriptors)
        faiss.write_index(index, str(index_path))
        np.savez_compressed(str(metadata_path), points3d=landmarks)

        feature_set = FeatureSet(
            scene_id=scene.id,
            index_path=str(index_path.resolve()),
            metadata_path=str(metadata_path.resolve()),
            num_descriptors=int(descriptors.shape[0]),
        )
        db.add(feature_set)
        scene.faiss_index_path = feature_set.index_path
        scene.feature_meta_path = feature_set.metadata_path
        db.add(scene)
        db.commit()
        db.refresh(feature_set)
        return feature_set

    @staticmethod
    def localize(scene_id: str, query_image_path: Path, db: Session) -> dict:
        scene = db.get(Scene, scene_id)
        if not scene:
            raise ValueError("Scene not found")

        feature_set = db.scalar(
            select(FeatureSet).where(FeatureSet.scene_id == scene_id).order_by(desc(FeatureSet.id))
        )
        if not feature_set:
            raise RuntimeError("Feature DB not built for this scene")

        index = faiss.read_index(feature_set.index_path)
        metadata = np.load(feature_set.metadata_path)
        points3d = metadata["points3d"].astype(np.float32)

        settings = get_settings()
        orb = cv2.ORB_create(nfeatures=settings.orb_nfeatures)
        result = VPSService._extract_frame_features(query_image_path, orb)
        if result is None:
            raise RuntimeError("No ORB features found in query image")
        keypoints, query_desc = result
        if query_desc.shape[0] < 8:
            raise RuntimeError("Not enough query descriptors for localization")
        query_desc = query_desc.astype(np.float32)

        D, I = index.search(query_desc, 2)
        image_points = []
        object_points = []
        for qi, neighbors in enumerate(I):
            if neighbors[0] < 0:
                continue
            d1 = D[qi][0]
            d2 = D[qi][1] if D.shape[1] > 1 else 1e9
            if d1 > 3000 or d1 >= 0.85 * d2:
                continue
            object_points.append(points3d[neighbors[0]])
            image_points.append(keypoints[qi].pt)

        if len(object_points) < 8:
            raise RuntimeError("Insufficient 2D-3D correspondences for PnP")

        object_points_arr = np.array(object_points, dtype=np.float32)
        image_points_arr = np.array(image_points, dtype=np.float32)
        camera_matrix = VPSService._estimate_query_intrinsics(scene_id, db)
        success, rvec, tvec, inliers = solve_pnp_pose(object_points_arr, image_points_arr, camera_matrix)
        if not success or len(inliers) < 6:
            raise RuntimeError("PnP failed to converge")

        R_cw, _ = cv2.Rodrigues(rvec)
        R_wc = R_cw.T
        C = (-R_wc @ tvec).reshape(3)
        quat_xyzw = rotmat_to_quaternion(R_wc)

        inlier_idx = inliers.reshape(-1)
        reproj, _ = cv2.projectPoints(
            object_points_arr[inlier_idx],
            rvec,
            tvec,
            camera_matrix,
            None,
        )
        reproj = reproj.reshape(-1, 2)
        err = np.mean(np.linalg.norm(reproj - image_points_arr[inlier_idx], axis=1))
        inlier_ratio = len(inlier_idx) / max(1, len(object_points_arr))
        confidence = max(0.0, min(1.0, inlier_ratio * 0.7 + max(0.0, 1.0 - err / 10.0) * 0.3))

        return {
            "position": [float(C[0]), float(C[1]), float(C[2])],
            "rotation": [float(quat_xyzw[0]), float(quat_xyzw[1]), float(quat_xyzw[2]), float(quat_xyzw[3])],
            "confidence": float(confidence),
        }

    @staticmethod
    def _extract_frame_features(image_path: Path, orb: cv2.ORB) -> tuple[list, np.ndarray] | None:
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            return None
        keypoints, descriptors = orb.detectAndCompute(image, None)
        if descriptors is None or len(keypoints) == 0:
            return None
        return keypoints, descriptors

    @staticmethod
    def _k_from_intrinsics(intrinsics: dict) -> np.ndarray:
        fx = float(intrinsics["fx"])
        fy = float(intrinsics["fy"])
        cx = float(intrinsics["cx"])
        cy = float(intrinsics["cy"])
        return np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)

    @staticmethod
    def _rt_from_pose(pose: dict) -> tuple[np.ndarray, np.ndarray]:
        R_cw = np.array(pose["rotation_cw"], dtype=np.float64)
        t_cw = np.array(pose["tvec"], dtype=np.float64)
        return R_cw, t_cw

    @staticmethod
    def _estimate_query_intrinsics(scene_id: str, db: Session) -> np.ndarray:
        frame = db.scalar(
            select(Frame)
            .where(Frame.scene_id == scene_id, Frame.intrinsics_json.is_not(None))
            .order_by(Frame.frame_index.asc())
        )
        if not frame:
            raise RuntimeError("No intrinsics available for scene")
        return VPSService._k_from_intrinsics(frame.intrinsics_json)
