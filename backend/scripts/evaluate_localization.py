"""Measure localization accuracy on a processed scene against COLMAP ground truth.

This runner calls the **product** code path (``VPSService.localize``) once per sampled
frame and compares the returned pose with the pose COLMAP registered for that image.
It exists because ``test_localization.py`` duplicates the matcher/PnP logic and drifted
away from the service.

Important limitation: the query frames are drawn from the same capture that built the
map, so the FAISS index already contains their descriptors. Treat the numbers as an
*optimistic* sanity check of the pipeline, not as a held-out benchmark. A held-out
number needs a separate capture session fed to ``benchmark_localization.py`` via a
``vps.real_benchmark.v1`` manifest.

Usage::

    python backend/scripts/evaluate_localization.py --scene-id <id> --num-frames 20
"""

from __future__ import annotations

import argparse
import json
import math
import random
import struct
import statistics
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy import select

from backend.models.frame import Frame
from backend.models.scene import Scene
from backend.services.vps import VPSService
from backend.utils.config import get_settings
from backend.utils.db import SessionLocal
from backend.utils.storage import get_storage


def read_colmap_poses(images_bin: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Parse ``images.bin`` into ``{image_name: (R_world_to_cam, t_world_to_cam)}``."""
    poses: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    with images_bin.open("rb") as handle:
        count = struct.unpack("<Q", handle.read(8))[0]
        for _ in range(count):
            handle.read(4)  # image_id
            qvec = np.array(struct.unpack("<4d", handle.read(32)), dtype=np.float64)
            tvec = np.array(struct.unpack("<3d", handle.read(24)), dtype=np.float64)
            handle.read(4)  # camera_id
            name_bytes = bytearray()
            while True:
                char = handle.read(1)
                if char == b"\x00":
                    break
                if not char:
                    raise RuntimeError(f"Unexpected end of {images_bin}")
                name_bytes.extend(char)
            num_points2d = struct.unpack("<Q", handle.read(8))[0]
            handle.read(24 * num_points2d)  # x, y, point3D_id per observation
            poses[name_bytes.decode()] = (quaternion_to_rotation(qvec), tvec)
    return poses


def quaternion_to_rotation(qvec: np.ndarray) -> np.ndarray:
    """COLMAP stores qvec as (w, x, y, z)."""
    w, x, y, z = qvec
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def camera_center(rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    """World-space position of the camera: ``C = -R^T t``."""
    return -rotation.T @ translation


def rotation_error_deg(pred_quat_xyzw: list[float], gt_rotation: np.ndarray) -> float:
    """Angle between the predicted camera rotation (xyzw) and the ground-truth one."""
    if len(pred_quat_xyzw) != 4:
        raise ValueError("Predicted rotation must have four components")
    x, y, z, w = pred_quat_xyzw
    # Quaternion (xyzw) -> rotation matrix.
    pred = np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )
    relative = pred @ gt_rotation.T
    cos_theta = max(-1.0, min(1.0, (float(np.trace(relative)) - 1.0) * 0.5))
    return math.degrees(math.acos(cos_theta))


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=np.float64), fraction))


def summarize(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "median": None, "p95": None, "mean": None, "max": None}
    return {
        "count": len(values),
        "median": percentile(values, 50),
        "p95": percentile(values, 95),
        "mean": float(statistics.fmean(values)),
        "max": float(max(values)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--num-frames", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model-dir", help="COLMAP model directory (default: recon/<scene>/sparse/0)")
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--min-inliers", type=int, default=30)
    parser.add_argument("--max-translation-error", type=float, default=0.5, help="metres, map units")
    parser.add_argument("--max-rotation-error", type=float, default=10.0, help="degrees")
    args = parser.parse_args()

    settings = get_settings()
    storage = get_storage()

    with SessionLocal() as db:
        scene = db.get(Scene, args.scene_id)
        if scene is None:
            raise SystemExit(f"Scene {args.scene_id} not found")
        if scene.status != "READY":
            print(f"WARNING: scene status is {scene.status}, not READY")

        model_dir = (
            Path(args.model_dir)
            if args.model_dir
            else storage.ensure_local_copy(f"recon/{args.scene_id}") / "sparse" / "0"
        )
        images_bin = model_dir / "images.bin"
        if not images_bin.exists():
            raise SystemExit(f"COLMAP model not found at {images_bin}")
        poses = read_colmap_poses(images_bin)

        frames = db.scalars(
            select(Frame).where(Frame.scene_id == args.scene_id).order_by(Frame.frame_index.asc())
        ).all()
        registered = [frame for frame in frames if Path(frame.image_path).name in poses]
        print(f"COLMAP registered images: {len(poses)} | DB frames: {len(frames)} | usable: {len(registered)}")
        if not registered:
            raise SystemExit("No DB frame matches a registered COLMAP image; nothing to evaluate")

        random.Random(args.seed).shuffle(registered)
        sample = registered[: max(1, min(args.num_frames, len(registered)))]

        rows = []
        for frame in sample:
            name = Path(frame.image_path).name
            ground_truth_rotation, ground_truth_translation = poses[name]
            gt_center = camera_center(ground_truth_rotation, ground_truth_translation)
            query_path = storage.ensure_local_copy(frame.image_path)
            entry: dict = {"frame": name, "frame_index": frame.frame_index}
            try:
                result = VPSService.localize(args.scene_id, query_path, db)
                pred_center = np.asarray(result["position"], dtype=np.float64)
                entry.update(
                    {
                        "ok": True,
                        "inliers": int(result.get("inliers", 0)),
                        "confidence": float(result.get("confidence", 0.0)),
                        "mode": result.get("mode"),
                        "translation_error": float(np.linalg.norm(pred_center - gt_center)),
                        "rotation_error_deg": rotation_error_deg(result["rotation"], ground_truth_rotation),
                    }
                )
            except Exception as exc:  # localization failure is a legitimate outcome
                entry.update({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]})
            rows.append(entry)
            print(
                f"  {name}: "
                + (
                    f"inliers={entry['inliers']} conf={entry['confidence']:.3f} "
                    f"trans={entry['translation_error']:.4f} rot={entry['rotation_error_deg']:.2f}deg"
                    if entry.get("ok")
                    else f"FAILED ({entry['error']})"
                )
            )

    solved = [row for row in rows if row.get("ok")]
    accepted = [
        row
        for row in solved
        if row["inliers"] >= args.min_inliers
        and row["translation_error"] <= args.max_translation_error
        and row["rotation_error_deg"] <= args.max_rotation_error
    ]
    report = {
        "schema": "vps.self_evaluation.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scene_id": args.scene_id,
        "caveat": (
            "Query frames come from the same capture as the map, so their descriptors are already in the "
            "FAISS index. These numbers are an optimistic pipeline sanity check, not a held-out benchmark."
        ),
        "settings": {
            "feature_mode": settings.feature_mode,
            "orb_nfeatures": settings.orb_nfeatures,
            "min_inliers": args.min_inliers,
            "max_translation_error": args.max_translation_error,
            "max_rotation_error": args.max_rotation_error,
            "seed": args.seed,
        },
        "counts": {
            "registered_images": len(poses),
            "db_frames": len(frames),
            "usable_frames": len(registered),
            "sampled": len(rows),
            "solved": len(solved),
            "failed_to_solve": len(rows) - len(solved),
            "accepted": len(accepted),
        },
        "success_rate": (len(accepted) / len(rows)) if rows else 0.0,
        "translation_error": summarize([row["translation_error"] for row in solved]),
        "rotation_error_deg": summarize([row["rotation_error_deg"] for row in solved]),
        "inliers": summarize([float(row["inliers"]) for row in solved]),
        "confidence": summarize([row["confidence"] for row in solved]),
        "frames": rows,
    }

    report_path = Path(args.report_path or f"backend/storage/debug/self_eval_{args.scene_id[:8]}.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print()
    print(f"sampled={report['counts']['sampled']} solved={report['counts']['solved']} "
          f"accepted={report['counts']['accepted']} success_rate={report['success_rate']:.1%}")
    for key in ("translation_error", "rotation_error_deg", "inliers", "confidence"):
        stats = report[key]
        if stats["count"]:
            print(f"  {key}: median={stats['median']:.4f} p95={stats['p95']:.4f} max={stats['max']:.4f}")
    print(f"report: {report_path.resolve()}")


if __name__ == "__main__":
    main()
