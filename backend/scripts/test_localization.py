import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

import cv2
import faiss
import numpy as np
from sqlalchemy import select

from backend.models.frame import Frame
from backend.models.scene import Scene
from backend.services.feature_mapper import FeatureMapper
from backend.services.feature_service import FeatureService
from backend.utils.db import SessionLocal
from backend.utils.config import get_settings


def rotation_error_deg(R_pred: np.ndarray, R_gt: np.ndarray) -> float:
    rel = R_pred @ R_gt.T
    trace_val = float(np.trace(rel))
    cos_theta = max(-1.0, min(1.0, (trace_val - 1.0) * 0.5))
    return float(math.degrees(math.acos(cos_theta)))


def summarize_distances(distances: list[float]) -> dict:
    if not distances:
        return {"count": 0}
    arr = np.array(distances, dtype=np.float32)
    return {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p90": float(np.percentile(arr, 90)),
        "max": float(np.max(arr)),
    }


def summarize_points3d(points3d: np.ndarray) -> dict:
    if points3d.size == 0:
        return {"count": 0}
    mins = np.min(points3d, axis=0)
    maxs = np.max(points3d, axis=0)
    stds = np.std(points3d, axis=0)
    diag = float(np.linalg.norm(maxs - mins))
    return {
        "count": int(points3d.shape[0]),
        "bbox_min": [float(mins[0]), float(mins[1]), float(mins[2])],
        "bbox_max": [float(maxs[0]), float(maxs[1]), float(maxs[2])],
        "std_xyz": [float(stds[0]), float(stds[1]), float(stds[2])],
        "bbox_diagonal": diag,
    }


def evaluate_frame(
    scene: Scene,
    frame: Frame,
    index: faiss.Index,
    db_descriptors: np.ndarray,
    db_points3d: np.ndarray,
    db_point_ids: np.ndarray,
    ratio: float,
    save_debug_path: Path | None = None,
) -> dict[str, Any]:
    query_keypoints_xy, query_descriptors = FeatureMapper.extract_orb_features(Path(frame.image_path))
    if query_descriptors.shape[0] < 8:
        return {
            "frame_index": frame.frame_index,
            "frame_id": frame.id,
            "vps_viable": False,
            "inliers": 0,
            "total_matches": 0,
            "confidence": 0.0,
            "translation_error": None,
            "rotation_error": None,
            "reprojection_error": None,
            "diagnostic_flags": ["LOW_MATCH_COUNT"],
            "failure_details": {
                "reason": "insufficient_query_features",
                "query_feature_count": int(query_descriptors.shape[0]),
                "match_distance_stats": {"count": 0},
                "points3d_distribution": {"count": 0},
            },
        }

    distances, neighbors = index.search(query_descriptors.astype(np.float32), 2)
    best_by_point: dict[int, tuple[float, np.ndarray, np.ndarray]] = {}
    kept_distances: list[float] = []
    for qi, nn in enumerate(neighbors):
        idx0 = int(nn[0])
        if idx0 < 0:
            continue
        d1 = float(distances[qi, 0])
        d2 = float(distances[qi, 1]) if distances.shape[1] > 1 else float("inf")
        if d1 >= ratio * d2:
            continue
        point_id = int(db_point_ids[idx0])
        candidate = (d1, db_points3d[idx0], query_keypoints_xy[qi])
        current = best_by_point.get(point_id)
        if current is None or d1 < current[0]:
            best_by_point[point_id] = candidate

    for item in best_by_point.values():
        kept_distances.append(float(item[0]))

    total_matches = len(best_by_point)
    if total_matches < 8:
        points3d_empty = (
            np.stack([v[1] for v in best_by_point.values()], axis=0).astype(np.float32)
            if best_by_point
            else np.empty((0, 3), dtype=np.float32)
        )
        return {
            "frame_index": frame.frame_index,
            "frame_id": frame.id,
            "vps_viable": False,
            "inliers": 0,
            "total_matches": total_matches,
            "confidence": 0.0,
            "translation_error": None,
            "rotation_error": None,
            "reprojection_error": None,
            "diagnostic_flags": ["LOW_MATCH_COUNT"],
            "failure_details": {
                "reason": "insufficient_correspondences",
                "match_distance_stats": summarize_distances(kept_distances),
                "points3d_distribution": summarize_points3d(points3d_empty),
            },
        }

    points3d = np.stack([v[1] for v in best_by_point.values()], axis=0).astype(np.float32)
    points2d = np.stack([v[2] for v in best_by_point.values()], axis=0).astype(np.float32)

    intr = frame.intrinsics_json
    fx, fy = float(intr["fx"]), float(intr["fy"])
    cx, cy = float(intr["cx"]), float(intr["cy"])
    camera_matrix = np.array([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)

    success, rvec, tvec, inliers = cv2.solvePnPRansac(
        objectPoints=points3d,
        imagePoints=points2d,
        cameraMatrix=camera_matrix,
        distCoeffs=None,
        reprojectionError=8.0,
        confidence=0.99,
        iterationsCount=100,
    )

    inlier_idx = inliers.reshape(-1) if inliers is not None else np.empty((0,), dtype=np.int32)
    inlier_count = int(inlier_idx.shape[0])
    confidence = float(inlier_count / max(total_matches, 1))
    translation_error = None
    rotation_error = None
    reprojection_error = None
    if success and inlier_count >= 4:
        R_cw, _ = cv2.Rodrigues(rvec)
        R_wc = R_cw.T
        C_pred = (-R_wc @ tvec).reshape(3)
        C_gt = np.array(frame.pose_json["position_wc"], dtype=np.float64)
        R_gt = np.array(frame.pose_json["rotation_wc"], dtype=np.float64)
        translation_error = float(np.linalg.norm(C_pred - C_gt))
        rotation_error = rotation_error_deg(R_wc, R_gt)
        inlier_points3d = points3d[inlier_idx]
        inlier_points2d = points2d[inlier_idx]
        projected, _ = cv2.projectPoints(inlier_points3d, rvec, tvec, camera_matrix, None)
        projected = projected.reshape(-1, 2)
        reprojection_error = float(np.mean(np.linalg.norm(projected - inlier_points2d, axis=1)))

    if save_debug_path is not None:
        draw_debug_image(
            image_path=Path(frame.image_path),
            points2d=points2d,
            points3d=points3d,
            inlier_idx=inlier_idx,
            rvec=rvec if success else None,
            tvec=tvec if success else None,
            camera_matrix=camera_matrix,
            output_path=save_debug_path,
        )

    flags: list[str] = []
    if total_matches < 30:
        flags.append("LOW_MATCH_COUNT")
    points3d_dist = summarize_points3d(points3d)
    if float(points3d_dist.get("bbox_diagonal", 0.0)) < 1.0:
        flags.append("POOR_3D_DISTRIBUTION")
    if reprojection_error is not None and reprojection_error > 5.0:
        flags.append("HIGH_REPROJECTION_ERROR")

    vps_viable = bool(
        success
        and inlier_count > 30
        and confidence > 0.3
        and translation_error is not None
        and rotation_error is not None
        and translation_error < 0.5
        and rotation_error < 10.0
    )

    result = {
        "frame_index": frame.frame_index,
        "frame_id": frame.id,
        "vps_viable": vps_viable,
        "inliers": inlier_count,
        "total_matches": total_matches,
        "confidence": confidence,
        "translation_error": translation_error,
        "rotation_error": rotation_error,
        "reprojection_error": reprojection_error,
        "diagnostic_flags": flags,
    }
    if not vps_viable:
        result["failure_details"] = {
            "solvepnp_success": bool(success),
            "match_distance_stats": summarize_distances(kept_distances),
            "points3d_distribution": points3d_dist,
        }
    return result


def draw_debug_image(
    image_path: Path,
    points2d: np.ndarray,
    points3d: np.ndarray,
    inlier_idx: np.ndarray,
    rvec: np.ndarray | None,
    tvec: np.ndarray | None,
    camera_matrix: np.ndarray,
    output_path: Path,
) -> None:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        return
    for p in points2d:
        cv2.circle(image, (int(round(p[0])), int(round(p[1]))), 2, (0, 255, 255), -1)
    if rvec is not None and tvec is not None and inlier_idx.size > 0:
        inlier_points2d = points2d[inlier_idx]
        inlier_points3d = points3d[inlier_idx]
        projected, _ = cv2.projectPoints(inlier_points3d, rvec, tvec, camera_matrix, None)
        projected = projected.reshape(-1, 2)
        for p_obs, p_proj in zip(inlier_points2d, projected):
            pt_obs = (int(round(p_obs[0])), int(round(p_obs[1])))
            pt_proj = (int(round(p_proj[0])), int(round(p_proj[1])))
            cv2.circle(image, pt_obs, 3, (0, 255, 0), -1)
            cv2.circle(image, pt_proj, 3, (255, 0, 0), 1)
            cv2.line(image, pt_obs, pt_proj, (255, 128, 0), 1)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), image)


def aggregate_results(scene_id: str, frame_results: list[dict[str, Any]]) -> dict[str, Any]:
    if not frame_results:
        return {
            "scene_id": scene_id,
            "num_frames": 0,
            "success_rate": 0.0,
            "avg_inliers": 0.0,
            "avg_confidence": 0.0,
            "avg_translation_error": None,
            "avg_rotation_error": None,
        }
    n = len(frame_results)
    success = sum(1 for r in frame_results if r["vps_viable"])
    avg_inliers = float(np.mean([r["inliers"] for r in frame_results]))
    avg_conf = float(np.mean([r["confidence"] for r in frame_results]))
    t_errs = [r["translation_error"] for r in frame_results if r["translation_error"] is not None]
    r_errs = [r["rotation_error"] for r in frame_results if r["rotation_error"] is not None]
    return {
        "scene_id": scene_id,
        "num_frames": n,
        "success_rate": float(success / n),
        "avg_inliers": avg_inliers,
        "avg_confidence": avg_conf,
        "avg_translation_error": float(np.mean(t_errs)) if t_errs else None,
        "avg_rotation_error": float(np.mean(r_errs)) if r_errs else None,
    }


def config_score(summary: dict[str, Any]) -> float:
    success = float(summary.get("success_rate", 0.0))
    inliers = float(summary.get("avg_inliers", 0.0))
    conf = float(summary.get("avg_confidence", 0.0))
    t = summary.get("avg_translation_error")
    r = summary.get("avg_rotation_error")
    t_penalty = float(t) if t is not None else 10.0
    r_penalty = float(r) if r is not None else 30.0
    return success * 100.0 + conf * 25.0 + min(inliers, 80.0) * 0.4 - t_penalty * 10.0 - r_penalty * 0.5


def select_sample_frames(all_frames: list[Frame], num_frames: int, seed: int) -> list[Frame]:
    if num_frames <= 0 or num_frames >= len(all_frames):
        return all_frames
    rng = random.Random(seed)
    picked = rng.sample(all_frames, num_frames)
    picked.sort(key=lambda f: f.frame_index)
    return picked


def run_config_evaluation(
    scene: Scene,
    frames: list[Frame],
    orb_nfeatures: int,
    pixel_threshold: float,
    ratio: float,
    debug_dir: Path,
    db,
) -> dict[str, Any]:
    settings = get_settings()
    original_nfeatures = settings.orb_nfeatures
    original_px_threshold = FeatureMapper.PIXEL_DISTANCE_THRESHOLD

    try:
        settings.orb_nfeatures = int(orb_nfeatures)
        FeatureMapper.PIXEL_DISTANCE_THRESHOLD = float(pixel_threshold)
        FeatureService.build_scene_feature_index(scene, db)
        db.refresh(scene)

        if not scene.faiss_index_path or not scene.feature_meta_path:
            raise RuntimeError("Feature index paths were not persisted after indexing")
        index = faiss.read_index(scene.faiss_index_path)
        meta = np.load(scene.feature_meta_path)
        db_descriptors = np.empty((0, 32), dtype=np.uint8)
        db_points3d = meta["points3d"].astype(np.float32)
        db_point_ids = meta["point3d_ids"].astype(np.int64)

        frame_results = []
        for frame in frames:
            frame_result = evaluate_frame(
                scene=scene,
                frame=frame,
                index=index,
                db_descriptors=db_descriptors,
                db_points3d=db_points3d,
                db_point_ids=db_point_ids,
                ratio=ratio,
                save_debug_path=None,
            )
            frame_results.append(frame_result)

        summary = aggregate_results(scene.id, frame_results)

        viable = [r for r in frame_results if r["vps_viable"]]
        non_viable = [r for r in frame_results if not r["vps_viable"]]
        viable_sorted = sorted(
            viable,
            key=lambda r: (
                -(r["confidence"] if r["confidence"] is not None else 0.0),
                r["translation_error"] if r["translation_error"] is not None else 1e9,
                r["rotation_error"] if r["rotation_error"] is not None else 1e9,
            ),
        )
        non_viable_sorted = sorted(
            non_viable,
            key=lambda r: (
                r["confidence"] if r["confidence"] is not None else 0.0,
                -(r["translation_error"] if r["translation_error"] is not None else 1e9),
                -(r["rotation_error"] if r["rotation_error"] is not None else 1e9),
            ),
        )
        best_cases = viable_sorted[:5]
        worst_cases = non_viable_sorted[:5]

        # Save 3-5 debug images for best and worst cases
        for bucket_name, cases in [("best", best_cases[:5]), ("worst", worst_cases[:5])]:
            for case in cases[:5]:
                target_frame = next((f for f in frames if f.frame_index == case["frame_index"]), None)
                if target_frame is None:
                    continue
                dbg_path = (
                    debug_dir
                    / f"cfg_orb{orb_nfeatures}_px{pixel_threshold}_r{ratio}"
                    / bucket_name
                    / f"frame_{target_frame.frame_index:06d}.jpg"
                )
                _ = evaluate_frame(
                    scene=scene,
                    frame=target_frame,
                    index=index,
                    db_descriptors=db_descriptors,
                    db_points3d=db_points3d,
                    db_point_ids=db_point_ids,
                    ratio=ratio,
                    save_debug_path=dbg_path,
                )

        return {
            "config": {
                "orb_nfeatures": orb_nfeatures,
                "pixel_distance_threshold": pixel_threshold,
                "ratio_test_threshold": ratio,
            },
            "summary": summary,
            "failures": [r for r in frame_results if not r["vps_viable"]],
            "best_case_frames": [r["frame_index"] for r in best_cases[:5]],
            "worst_case_frames": [r["frame_index"] for r in worst_cases[:5]],
            "score": config_score(summary),
        }
    finally:
        settings.orb_nfeatures = original_nfeatures
        FeatureMapper.PIXEL_DISTANCE_THRESHOLD = original_px_threshold


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch VPS localization evaluator with parameter sweep.")
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--frame-index", type=int, default=None)
    parser.add_argument("--num-frames", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--debug-dir", default="backend/storage/debug")
    parser.add_argument("--report-path", default="backend/storage/debug/vps_evaluation_report.json")
    parser.add_argument("--orb-nfeatures", default="500,1000,2000")
    parser.add_argument("--pixel-thresholds", default="3,5,8")
    parser.add_argument("--ratio-thresholds", default="0.7,0.8")
    args = parser.parse_args()

    orb_nfeatures_list = [int(x.strip()) for x in args.orb_nfeatures.split(",") if x.strip()]
    pixel_threshold_list = [float(x.strip()) for x in args.pixel_thresholds.split(",") if x.strip()]
    ratio_threshold_list = [float(x.strip()) for x in args.ratio_thresholds.split(",") if x.strip()]

    db = SessionLocal()
    try:
        scene = db.get(Scene, args.scene_id)
        if scene is None:
            raise SystemExit(f"Scene not found: {args.scene_id}")

        all_frames = db.scalars(
            select(Frame)
            .where(
                Frame.scene_id == args.scene_id,
                Frame.pose_json.is_not(None),
                Frame.intrinsics_json.is_not(None),
            )
            .order_by(Frame.frame_index.asc())
        ).all()
        if not all_frames:
            raise SystemExit("No frames with GT pose/intrinsics found for scene")

        if args.frame_index is not None:
            eval_frames = [f for f in all_frames if f.frame_index == args.frame_index]
            if not eval_frames:
                raise SystemExit(f"frame_index not found in GT-capable frames: {args.frame_index}")
        else:
            eval_frames = select_sample_frames(all_frames, args.num_frames, args.seed)

        debug_dir = Path(args.debug_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)

        config_results = []
        for orb_nf in orb_nfeatures_list:
            for px in pixel_threshold_list:
                for ratio in ratio_threshold_list:
                    try:
                        result = run_config_evaluation(
                            scene=scene,
                            frames=eval_frames,
                            orb_nfeatures=orb_nf,
                            pixel_threshold=px,
                            ratio=ratio,
                            debug_dir=debug_dir,
                            db=db,
                        )
                    except Exception as e:  # noqa: BLE001
                        result = {
                            "config": {
                                "orb_nfeatures": orb_nf,
                                "pixel_distance_threshold": px,
                                "ratio_test_threshold": ratio,
                            },
                            "summary": {
                                "scene_id": scene.id,
                                "num_frames": len(eval_frames),
                                "success_rate": 0.0,
                                "avg_inliers": 0.0,
                                "avg_confidence": 0.0,
                                "avg_translation_error": None,
                                "avg_rotation_error": None,
                            },
                            "failures": [{"error": str(e)}],
                            "best_case_frames": [],
                            "worst_case_frames": [],
                            "score": -9999.0,
                        }
                    config_results.append(result)

        ranked = sorted(config_results, key=lambda r: r.get("score", -9999.0), reverse=True)
        best_cfg = ranked[0] if ranked else None
        worst_cfg = ranked[-1] if ranked else None

        report = {
            "scene_id": scene.id,
            "num_frames": len(eval_frames),
            "sampled_frame_indices": [f.frame_index for f in eval_frames],
            "best_config": best_cfg,
            "worst_config": worst_cfg,
            "recommended_settings": best_cfg["config"] if best_cfg else None,
            "config_results": config_results,
        }

        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        # Output the requested top-level summary using best config.
        if best_cfg:
            best_summary = best_cfg["summary"]
            summary_output = {
                "scene_id": scene.id,
                "num_frames": best_summary["num_frames"],
                "success_rate": best_summary["success_rate"],
                "avg_inliers": best_summary["avg_inliers"],
                "avg_confidence": best_summary["avg_confidence"],
                "avg_translation_error": best_summary["avg_translation_error"],
                "avg_rotation_error": best_summary["avg_rotation_error"],
                "report_path": str(report_path.resolve()),
            }
        else:
            summary_output = {
                "scene_id": scene.id,
                "num_frames": len(eval_frames),
                "success_rate": 0.0,
                "avg_inliers": 0.0,
                "avg_confidence": 0.0,
                "avg_translation_error": None,
                "avg_rotation_error": None,
                "report_path": str(report_path.resolve()),
            }
        print(json.dumps(summary_output, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
