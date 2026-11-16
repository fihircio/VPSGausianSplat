"""Run a fixed-configuration localization benchmark on held-out real captures.

The query images must come from a capture session separate from the session used
to build the map. Ground-truth poses must already be expressed in the map's
scene coordinate frame. This runner does not tune localization parameters.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy import desc

from backend.models.frame import Frame
from backend.models.feature_set import FeatureSet
from backend.models.scene import Scene
from backend.services.vps import VPSService
from backend.utils.config import get_settings
from backend.utils.db import SessionLocal


SCHEMA_VERSION = "vps.real_benchmark.v1"
MAX_TRANSLATION_ERROR_M = 0.5
MAX_ROTATION_ERROR_DEG = 10.0
MIN_INLIERS = 30
MIN_CONFIDENCE = 0.3


def _quantile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=np.float64), percentile))


def _stats(values: list[float], unit: str) -> dict[str, Any]:
    return {
        "count": len(values),
        "unit": unit,
        "median": _quantile(values, 50),
        "p95": _quantile(values, 95),
        "mean": float(statistics.fmean(values)) if values else None,
    }


def _rotation_error_deg(q1_xyzw: list[float], q2_xyzw: list[float]) -> float:
    q1 = np.asarray(q1_xyzw, dtype=np.float64)
    q2 = np.asarray(q2_xyzw, dtype=np.float64)
    if q1.shape != (4,) or q2.shape != (4,):
        raise ValueError("rotation_xyzw must contain exactly four values")
    norm1, norm2 = float(np.linalg.norm(q1)), float(np.linalg.norm(q2))
    if norm1 == 0 or norm2 == 0:
        raise ValueError("rotation_xyzw cannot be a zero quaternion")
    q1, q2 = q1 / norm1, q2 / norm2
    dot = float(np.clip(abs(np.dot(q1, q2)), 0.0, 1.0))
    return float(math.degrees(2.0 * math.acos(dot)))


def _resolve_image_path(raw_path: str, manifest_path: Path) -> Path:
    image_path = Path(raw_path).expanduser()
    if not image_path.is_absolute():
        image_path = manifest_path.parent / image_path
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise ValueError(f"Query image does not exist: {image_path}")
    return image_path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read benchmark manifest {path}: {exc}") from exc

    if not isinstance(manifest, dict):
        raise SystemExit("benchmark manifest must be a JSON object")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit(f"schema_version must be {SCHEMA_VERSION!r}")
    if manifest.get("dataset_type") != "real_device_capture":
        raise SystemExit("dataset_type must be 'real_device_capture'; synthetic data uses a separate report")
    if manifest.get("split") != "held_out":
        raise SystemExit("split must be 'held_out'; do not score map/training frames")
    if manifest.get("coordinate_frame") != "scene_local":
        raise SystemExit("coordinate_frame must be 'scene_local' to match the map pose output")
    if not isinstance(manifest.get("ground_truth_source"), str) or not manifest["ground_truth_source"].strip():
        raise SystemExit("ground_truth_source must describe how independent ground truth was obtained")
    if not isinstance(manifest.get("benchmark_id"), str) or not manifest["benchmark_id"].strip():
        raise SystemExit("benchmark_id is required")
    map_capture = manifest.get("map_capture_session_id")
    if not isinstance(map_capture, str) or not map_capture.strip():
        raise SystemExit("map_capture_session_id is required")
    queries = manifest.get("queries")
    if not isinstance(queries, list) or not queries:
        raise SystemExit("queries must be a non-empty list")

    query_ids: set[str] = set()
    for index, query in enumerate(queries):
        label = f"queries[{index}]"
        if not isinstance(query, dict):
            raise SystemExit(f"{label} must be an object")
        query_id = query.get("query_id")
        if not isinstance(query_id, str) or not query_id.strip() or query_id in query_ids:
            raise SystemExit(f"{label}.query_id must be a unique non-empty string")
        query_ids.add(query_id)
        capture_id = query.get("capture_session_id")
        if not isinstance(capture_id, str) or not capture_id.strip():
            raise SystemExit(f"{label}.capture_session_id is required")
        if capture_id == map_capture:
            raise SystemExit(f"{label} is from the map capture session; held-out queries need a separate session")
        if not isinstance(query.get("image_path"), str):
            raise SystemExit(f"{label}.image_path is required")
        metadata = query.get("metadata")
        if not isinstance(metadata, dict):
            raise SystemExit(f"{label}.metadata is required")
        for required_metadata in ("site", "device_model", "lighting"):
            if not isinstance(metadata.get(required_metadata), str) or not metadata[required_metadata].strip():
                raise SystemExit(f"{label}.metadata.{required_metadata} is required")
        gt = query.get("ground_truth")
        if not isinstance(gt, dict):
            raise SystemExit(f"{label}.ground_truth is required")
        position = gt.get("position_m")
        rotation = gt.get("rotation_xyzw")
        if not isinstance(position, list) or len(position) != 3:
            raise SystemExit(f"{label}.ground_truth.position_m must contain three values")
        if not isinstance(rotation, list) or len(rotation) != 4:
            raise SystemExit(f"{label}.ground_truth.rotation_xyzw must contain four values")
        try:
            numeric_values = [float(value) for value in position + rotation]
            if not all(math.isfinite(value) for value in numeric_values):
                raise ValueError
            if float(np.linalg.norm(np.asarray(rotation, dtype=np.float64))) == 0:
                raise ValueError
        except (TypeError, ValueError):
            raise SystemExit(f"{label}.ground_truth pose values must be finite numbers with a nonzero quaternion")

    return manifest


def _failure_category(exc: Exception) -> str:
    message = str(exc).lower()
    if "not enough" in message or "feature" in message:
        return "insufficient_features"
    if "inlier" in message or "match" in message or "correspondence" in message:
        return "insufficient_matches_or_inliers"
    if isinstance(exc, ValueError) and "scene" in message:
        return "scene_or_map_unavailable"
    if isinstance(exc, RuntimeError):
        return "localization_rejected"
    return "localization_error"


def _check_exact_map_frame_duplicates(
    db, scene_id: str, query_paths: list[Path]
) -> dict[str, int]:
    """Reject exact file/path reuse against locally accessible map frames."""
    query_paths_by_hash = {_sha256(path): path for path in query_paths}
    query_resolved = {str(path.resolve()) for path in query_paths}
    frame_paths = db.scalars(select(Frame.image_path).where(Frame.scene_id == scene_id)).all()
    hashes_checked = 0
    unavailable = 0
    for raw in frame_paths:
        if not raw:
            continue
        frame_path = Path(raw).expanduser()
        if not frame_path.is_absolute():
            frame_path = Path.cwd() / frame_path
        frame_path = frame_path.resolve()
        if str(frame_path) in query_resolved:
            raise SystemExit(f"Held-out query reuses a map-frame path: {frame_path}")
        if not frame_path.is_file():
            unavailable += 1
            continue
        hashes_checked += 1
        overlap = _sha256(frame_path)
        if overlap in query_paths_by_hash:
            raise SystemExit(
                "Held-out query file exactly matches a stored map frame: "
                f"{query_paths_by_hash[overlap]}"
            )
    return {"map_frame_files_hash_checked": hashes_checked, "map_frame_files_unavailable": unavailable}


def _acceptance_failure(result: dict[str, Any], translation_error: float, rotation_error: float) -> str | None:
    if int(result.get("inliers", 0)) <= MIN_INLIERS:
        return "below_minimum_inliers"
    if float(result.get("confidence", 0.0)) <= MIN_CONFIDENCE:
        return "below_minimum_confidence"
    if translation_error >= MAX_TRANSLATION_ERROR_M:
        return "translation_error_over_limit"
    if rotation_error >= MAX_ROTATION_ERROR_DEG:
        return "rotation_error_over_limit"
    return None


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    returned = [row for row in rows if row["localization_returned"]]
    accepted = [row for row in returned if row["acceptance_failure"] is None]
    translation_errors = [row["translation_error_m"] for row in returned if row["translation_error_m"] is not None]
    rotation_errors = [row["rotation_error_deg"] for row in returned if row["rotation_error_deg"] is not None]
    return {
        "query_count": len(rows),
        "localization_returned_count": len(returned),
        "accepted_count": len(accepted),
        "success_rate": len(accepted) / len(rows) if rows else None,
        "translation_error_m": _stats(translation_errors, "m"),
        "rotation_error_deg": _stats(rotation_errors, "degrees"),
        "service_latency_ms": _stats([row["service_latency_ms"] for row in rows], "ms"),
        "failure_categories": dict(Counter(
            row["failure_category"] or row["acceptance_failure"]
            for row in rows
            if row["failure_category"] or row["acceptance_failure"]
        )),
    }


def _group_summary(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["metadata"].get(key) or "unknown"].append(row)
    return {name: _summarize(group) for name, group in sorted(groups.items())}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate fixed VPS localization behavior on held-out real-device query frames."
    )
    parser.add_argument("--manifest", required=True, help="Path to a vps.real_benchmark.v1 JSON manifest")
    parser.add_argument("--report", help="Output report JSON (default: <manifest>.report.json)")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = _load_manifest(manifest_path)
    scene_id = manifest.get("scene_id")
    if not isinstance(scene_id, str) or not scene_id.strip():
        raise SystemExit("scene_id is required")

    prepared: list[tuple[dict[str, Any], Path]] = []
    for query in manifest["queries"]:
        image_path = _resolve_image_path(query["image_path"], manifest_path)
        prepared.append((query, image_path))

    db = SessionLocal()
    try:
        if db.get(Scene, scene_id) is None:
            raise SystemExit(f"Scene not found: {scene_id}")
        feature_sets = db.scalars(
            select(FeatureSet).where(FeatureSet.scene_id == scene_id).order_by(desc(FeatureSet.id))
        ).all()
        feature_set_snapshot = [
            {
                "id": feature_set.id,
                "feature_mode": feature_set.feature_mode,
                "num_descriptors": feature_set.num_descriptors,
                "created_at": feature_set.created_at.isoformat() if feature_set.created_at else None,
            }
            for feature_set in feature_sets
        ]
        runtime_settings = get_settings()
        duplicate_check = _check_exact_map_frame_duplicates(
            db, scene_id, [path for _, path in prepared]
        )
        rows: list[dict[str, Any]] = []
        for query, image_path in prepared:
            row: dict[str, Any] = {
                "query_id": query["query_id"],
                "capture_session_id": query["capture_session_id"],
                "metadata": {
                    "site": query.get("metadata", {}).get("site"),
                    "device_model": query.get("metadata", {}).get("device_model"),
                    "lens_mode": query.get("metadata", {}).get("lens_mode"),
                    "lighting": query.get("metadata", {}).get("lighting"),
                    "location_tag": query.get("metadata", {}).get("location_tag"),
                },
                "localization_returned": False,
                "failure_category": None,
                "acceptance_failure": None,
                "service_latency_ms": None,
                "inliers": None,
                "confidence": None,
                "translation_error_m": None,
                "rotation_error_deg": None,
            }
            started = time.perf_counter()
            try:
                result = VPSService.localize_image(
                    scene_id=scene_id,
                    query_image_path=str(image_path),
                    db=db,
                )
                row["localization_returned"] = True
                position = np.asarray(result["position"], dtype=np.float64)
                gt_position = np.asarray(query["ground_truth"]["position_m"], dtype=np.float64)
                row["translation_error_m"] = float(np.linalg.norm(position - gt_position))
                row["rotation_error_deg"] = _rotation_error_deg(
                    list(result["rotation"]), query["ground_truth"]["rotation_xyzw"]
                )
                row["inliers"] = int(result.get("inliers", 0))
                row["confidence"] = float(result.get("confidence", 0.0))
                row["mode"] = result.get("mode")
                row["acceptance_failure"] = _acceptance_failure(
                    result, row["translation_error_m"], row["rotation_error_deg"]
                )
            except Exception as exc:  # Per-query failures are part of the benchmark result.
                row["failure_category"] = _failure_category(exc)
                row["failure_detail"] = f"{type(exc).__name__}: {exc}"
            finally:
                row["service_latency_ms"] = (time.perf_counter() - started) * 1000.0
            rows.append(row)
            print(
                f"{query['query_id']}: returned={row['localization_returned']} "
                f"failure={row['failure_category'] or row['acceptance_failure'] or 'none'}"
            )
    finally:
        db.close()

    summary = _summarize(rows)
    report = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": manifest.get("benchmark_id"),
        "dataset_type": "real_device_capture",
        "split": "held_out",
        "scene_id": scene_id,
        "map_capture_session_id": manifest["map_capture_session_id"],
        "ground_truth_source": manifest.get("ground_truth_source"),
        "coordinate_frame": manifest.get("coordinate_frame"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "parameter_tuning": False,
            "localization_path": "VPSService.localize_image",
            "feature_sets_latest_first": feature_set_snapshot,
            "feature_settings": {
                "feature_mode": runtime_settings.feature_mode,
                "orb_nfeatures": runtime_settings.orb_nfeatures,
                "sp_max_keypoints": runtime_settings.sp_max_keypoints,
                "sp_conf_threshold": runtime_settings.sp_conf_threshold,
            },
            "acceptance": {
                "minimum_inliers_exclusive": MIN_INLIERS,
                "minimum_confidence_exclusive": MIN_CONFIDENCE,
                "maximum_translation_error_m_exclusive": MAX_TRANSLATION_ERROR_M,
                "maximum_rotation_error_deg_exclusive": MAX_ROTATION_ERROR_DEG,
            },
            "latency_scope": "in-process localization service; excludes HTTP, upload, and network latency",
        },
        "data_integrity": duplicate_check,
        "summary": summary,
        "by_device_model": _group_summary(rows, "device_model"),
        "by_lighting": _group_summary(rows, "lighting"),
        "by_site": _group_summary(rows, "site"),
        "queries": rows,
        "pilot_gate": {
            "success_rate_minimum": 0.6,
            "passed": bool(summary["success_rate"] is not None and summary["success_rate"] >= 0.6),
            "note": "Apply only to this scene/device/lighting/sample. A pass is not a production SLA.",
        },
    }

    report_path = Path(args.report).expanduser().resolve() if args.report else manifest_path.with_suffix(".report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"summary": summary, "report_path": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
