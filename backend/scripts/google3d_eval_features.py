#!/usr/bin/env python3
"""Run feature extraction and matching benchmarks across multiple feature modes."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from backend.services.google3d.aoi import AOIRegistry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="AOI registry JSON config")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("backend/storage/google3d"),
        help="Root folder for Google 3D scaffold output",
    )
    parser.add_argument("--aoi-id", help="AOI ID to evaluate; defaults to first in config")
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["ORB", "SIFT"],
        help="Feature extraction modes to evaluate (e.g. ORB SIFT DISK)",
    )
    return parser.parse_args()


def benchmark_mode(
    mode: str,
    image_paths: list[Path]
) -> dict[str, Any]:
    """Run extraction and consecutive matching benchmark for a single feature mode."""
    print(f"Benchmarking mode: {mode} across {len(image_paths)} frames...")
    
    extraction_times = []
    keypoint_counts = []
    keypoints_list = []
    descriptors_list = []
    
    # 1. Extraction Phase (direct OpenCV, no torch dependency)
    for path in image_paths:
        t0 = time.perf_counter()
        try:
            image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                raise RuntimeError(f"Cannot read {path}")
            upper = mode.upper()
            if upper == "ORB":
                det = cv2.ORB_create(nfeatures=3000)
                kps, descs = det.detectAndCompute(image, None)
                if descs is None or not kps:
                    kps_xy = np.empty((0, 2), dtype=np.float32)
                    descs = np.empty((0, 32), dtype=np.uint8)
                else:
                    kps_xy = np.array([kp.pt for kp in kps], dtype=np.float32)
                    descs = descs.astype(np.uint8)
            elif upper == "SIFT":
                det = cv2.SIFT_create()
                kps, descs = det.detectAndCompute(image, None)
                if descs is None or not kps:
                    kps_xy = np.empty((0, 2), dtype=np.float32)
                    descs = np.empty((0, 128), dtype=np.float32)
                else:
                    kps_xy = np.array([kp.pt for kp in kps], dtype=np.float32)
                    descs = descs.astype(np.float32)
            else:
                raise ValueError(f"Unsupported mode: {mode}")
        except Exception as e:
            print(f"Warning: Extraction failed on {path.name}: {e}", file=sys.stderr)
            kps_xy = np.empty((0, 2), dtype=np.float32)
            descs = np.empty((0, 0))
            
        t1 = time.perf_counter()
        
        extraction_times.append(t1 - t0)
        keypoint_counts.append(len(kps_xy))
        keypoints_list.append(kps_xy)
        descriptors_list.append(descs)
        
    # 2. Matching Phase (consecutive frames)
    match_counts = []
    inlier_counts = []
    inlier_ratios = []
    
    # Configure matcher based on feature type
    if mode.upper() in ("ORB",):
        # ORB uses Hamming distance
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    else:
        # SIFT/DISK use L2 norm
        matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
        
    for idx in range(len(image_paths) - 1):
        desc1 = descriptors_list[idx]
        desc2 = descriptors_list[idx + 1]
        
        kp1 = keypoints_list[idx]
        kp2 = keypoints_list[idx + 1]
        
        if desc1 is None or desc2 is None or len(desc1) < 4 or len(desc2) < 4:
            match_counts.append(0)
            inlier_counts.append(0)
            inlier_ratios.append(0.0)
            continue
            
        # Match features
        matches = matcher.match(desc1, desc2)
        match_counts.append(len(matches))
        
        if len(matches) < 4:
            inlier_counts.append(0)
            inlier_ratios.append(0.0)
            continue
            
        # Estimate Homography with RANSAC to find inliers
        pts1 = np.float32([kp1[m.queryIdx] for m in matches]).reshape(-1, 1, 2)
        pts2 = np.float32([kp2[m.trainIdx] for m in matches]).reshape(-1, 1, 2)
        
        _, mask = cv2.findHomography(pts1, pts2, cv2.RANSAC, 5.0)
        
        inliers = int(np.sum(mask)) if mask is not None else 0
        inlier_counts.append(inliers)
        inlier_ratios.append(inliers / len(matches) if len(matches) > 0 else 0.0)
        
    # Calculate statistics
    avg_kp = float(np.mean(keypoint_counts))
    median_kp = float(np.median(keypoint_counts))
    avg_time_ms = float(np.mean(extraction_times) * 1000)
    
    avg_matches = float(np.mean(match_counts)) if match_counts else 0.0
    median_inliers = float(np.median(inlier_counts)) if inlier_counts else 0.0
    avg_inlier_ratio = float(np.mean(inlier_ratios)) if inlier_ratios else 0.0
    
    return {
        "mode": mode,
        "frames_processed": len(image_paths),
        "keypoints": {
            "mean": avg_kp,
            "median": median_kp,
            "min": int(np.min(keypoint_counts)) if keypoint_counts else 0,
            "max": int(np.max(keypoint_counts)) if keypoint_counts else 0,
        },
        "performance": {
            "mean_extraction_time_ms": avg_time_ms,
            "fps": 1.0 / (avg_time_ms / 1000.0) if avg_time_ms > 0 else 0.0,
        },
        "matching": {
            "mean_matches": avg_matches,
            "median_inliers": median_inliers,
            "mean_inlier_ratio": avg_inlier_ratio,
        }
    }


def main() -> None:
    args = parse_args()
    
    # Load AOI registry
    registry = AOIRegistry.load(args.config)
    aoi = registry.get(args.aoi_id) if args.aoi_id else registry.aois[0]
    
    aoi_dir = args.output_root / "aois" / aoi.aoi_id
    rgb_dir = aoi_dir / "render_runs" / "scaffold" / "rgb"
    
    if not rgb_dir.exists():
        print(f"Error: Rendered frames not found at {rgb_dir}. Run google3d_render_dataset.py first.", file=sys.stderr)
        sys.exit(1)
        
    # Find all png files and sort them deterministically
    image_paths = sorted(list(rgb_dir.glob("*.png")))
    if not image_paths:
        print(f"Error: No images found in {rgb_dir}", file=sys.stderr)
        sys.exit(1)
    # Sample evenly for faster eval (max 500 frames per run)
    if len(image_paths) > 500:
        step = len(image_paths) // 500
        image_paths = image_paths[::step]
        
    print(f"Found {len(image_paths)} rendered images for evaluation (sampled).")
    
    results = []
    for mode in args.modes:
        res = benchmark_mode(mode, image_paths)
        results.append(res)
        
    # Output schema-compatible report
    report = {
        "schema_version": "google3d.feature_benchmark.v1",
        "aoi_id": aoi.aoi_id,
        "aoi_name": aoi.name,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "image_width": 1280,  # default scaffold resolution
        "image_height": 720,
        "benchmarks": results
    }
    
    # Save report
    eval_dir = aoi_dir / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    report_path = eval_dir / "feature_benchmark.json"
    
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        
    print(f"\nBenchmark report successfully saved to: {report_path}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
