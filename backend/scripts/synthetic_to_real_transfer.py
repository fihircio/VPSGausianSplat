#!/usr/bin/env python3
"""
Synthetic-to-Real Domain Transfer Check.

Cross-evaluates feature extractors across synthetic (Google 3D procedural renders)
and real-world (phone-captured VPS scene) domains.

Metrics:
  - Within-domain baselines: synth→synth, real→real
  - Cross-domain: synth→real, real→synth
  - Match counts, inlier ratios, feature descriptor distance distributions

Usage:
  # With DB (PostgreSQL must be running):
  python -m backend.scripts.synthetic_to_real_transfer \\
    --aoi-id klcc_001 --scene-id <uuid>

  # With direct image paths (no DB needed):
  python -m backend.scripts.synthetic_to_real_transfer \\
    --aoi-id klcc_001 --real-dir backend/storage/frames/<scene_uuid> \\
    --real-name "My Real Scene"
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def extract_features(mode: str, image_path: Path) -> tuple[np.ndarray, np.ndarray]:
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return np.empty((0, 2), dtype=np.float32), np.empty((0, 0))

    if mode.upper() == "ORB":
        det = cv2.ORB_create(nfeatures=3000)
        kps, descs = det.detectAndCompute(image, None)
        if descs is None or not kps:
            return np.empty((0, 2), dtype=np.float32), np.empty((0, 0))
        kps_xy = np.array([kp.pt for kp in kps], dtype=np.float32)
        return kps_xy, descs.astype(np.uint8)
    elif mode.upper() == "SIFT":
        det = cv2.SIFT_create()
        kps, descs = det.detectAndCompute(image, None)
        if descs is None or not kps:
            return np.empty((0, 2), dtype=np.float32), np.empty((0, 0))
        kps_xy = np.array([kp.pt for kp in kps], dtype=np.float32)
        return kps_xy, descs.astype(np.float32)
    else:
        raise ValueError(f"Unsupported feature mode: {mode}")


def match_and_evaluate(
    desc1: np.ndarray,
    desc2: np.ndarray,
    kp1: np.ndarray,
    kp2: np.ndarray,
    mode: str,
) -> dict[str, Any]:
    if desc1.shape[0] < 4 or desc2.shape[0] < 4:
        return {
            "matches": 0,
            "inliers": 0,
            "inlier_ratio": 0.0,
            "mean_distance": None,
            "median_distance": None,
        }

    norm = cv2.NORM_HAMMING if mode.upper() == "ORB" else cv2.NORM_L2
    matcher = cv2.BFMatcher(norm, crossCheck=True)
    matches = matcher.match(desc1, desc2)

    if len(matches) < 4:
        return {
            "matches": len(matches),
            "inliers": 0,
            "inlier_ratio": 0.0,
            "mean_distance": float(np.mean([m.distance for m in matches])),
            "median_distance": float(np.median([m.distance for m in matches])),
        }

    pts1 = np.float32([kp1[m.queryIdx] for m in matches]).reshape(-1, 1, 2)
    pts2 = np.float32([kp2[m.trainIdx] for m in matches]).reshape(-1, 1, 2)

    _, mask = cv2.findHomography(pts1, pts2, cv2.RANSAC, 5.0)
    inliers = int(np.sum(mask)) if mask is not None else 0

    distances = [m.distance for m in matches]
    return {
        "matches": len(matches),
        "inliers": inliers,
        "inlier_ratio": inliers / len(matches) if len(matches) > 0 else 0.0,
        "mean_distance": float(np.mean(distances)),
        "median_distance": float(np.median(distances)),
    }


def load_images_from_dir(path: Path, name: str, max_frames: int, ext: str = "*") -> list[Path]:
    if not path.exists():
        print(f"  Error: {name} directory not found: {path}")
        return []
    if ext != "*":
        paths = sorted(path.glob(f"*.{ext}"))
    else:
        paths = sorted([p for p in path.iterdir() if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png")])
    if not paths:
        print(f"  Error: No images found in {path}")
        return []
    if len(paths) > max_frames:
        step = len(paths) // max_frames
        paths = paths[::step]
    print(f"  Found {len(paths)} {name} images from {path}")
    return paths


def evaluate_domain(
    name_a: str,
    images_a: list[Path],
    name_b: str,
    images_b: list[Path],
    mode: str,
    max_pairs: int = 200,
) -> dict[str, Any]:
    print(f"  Evaluating {name_a}->{name_b} ({mode})...", end=" ")

    results = []
    step_a = max(1, len(images_a) // max(int(np.sqrt(max_pairs)), 1))
    step_b = max(1, len(images_b) // max(int(np.sqrt(max_pairs)), 1))

    for i in range(0, len(images_a), step_a):
        kp1, desc1 = extract_features(mode, images_a[i])
        if desc1.shape[0] < 4:
            continue
        for j in range(0, len(images_b), step_b):
            kp2, desc2 = extract_features(mode, images_b[j])
            if desc2.shape[0] < 4:
                continue
            res = match_and_evaluate(desc1, desc2, kp1, kp2, mode)
            res["src_index"] = i
            res["dst_index"] = j
            results.append(res)

    if not results:
        print("no valid pairs")
        return {
            "domain_pair": f"{name_a}->{name_b}",
            "mode": mode,
            "pairs_evaluated": 0,
            "mean_matches": 0.0,
            "mean_inliers": 0.0,
            "mean_inlier_ratio": 0.0,
            "mean_distance": None,
        }

    matches_arr = np.array([r["matches"] for r in results])
    inliers_arr = np.array([r["inliers"] for r in results])
    ratios_arr = np.array([r["inlier_ratio"] for r in results])
    dists = [r["mean_distance"] for r in results if r["mean_distance"] is not None]
    print(f"{len(results)} pairs")

    return {
        "domain_pair": f"{name_a}->{name_b}",
        "mode": mode,
        "pairs_evaluated": len(results),
        "match_stats": {
            "mean": float(np.mean(matches_arr)),
            "median": float(np.median(matches_arr)),
            "min": int(np.min(matches_arr)),
            "max": int(np.max(matches_arr)),
        },
        "inlier_stats": {
            "mean": float(np.mean(inliers_arr)),
            "median": float(np.median(inliers_arr)),
            "min": int(np.min(inliers_arr)),
            "max": int(np.max(inliers_arr)),
        },
        "inlier_ratio": {
            "mean": float(np.mean(ratios_arr)),
            "median": float(np.median(ratios_arr)),
            "std": float(np.std(ratios_arr)),
        },
        "descriptor_distance": {
            "mean": float(np.mean(dists)) if dists else None,
            "median": float(np.median(dists)) if dists else None,
        } if dists else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aoi-id", required=True, help="Synthetic AOI ID (e.g. klcc_001)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scene-id", help="Real scene UUID from DB (needs PostgreSQL running)")
    group.add_argument("--real-dir", type=Path, help="Directory of real-world images (no DB needed)")
    parser.add_argument("--real-name", default="real", help="Label for the real dataset (default: 'real')")
    parser.add_argument(
        "--google3d-root",
        type=Path,
        default=Path("backend/storage/google3d"),
        help="Google 3D storage root",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["ORB", "SIFT"],
        help="Feature modes to evaluate",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=200,
        help="Max frames per domain for cross-evaluation",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: google3d/aois/{aoi_id}/eval/transfer_check.json)",
    )
    args = parser.parse_args()

    aoi_dir = args.google3d_root / "aois" / args.aoi_id
    if not aoi_dir.exists():
        print(f"Error: AOI directory not found: {aoi_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"{'='*60}")
    print(f"Synthetic-to-Real Transfer Check")
    print(f"{'='*60}")
    print(f"Synthetic AOI: {args.aoi_id}")

    synth_images = load_images_from_dir(
        aoi_dir / "render_runs" / "scaffold" / "rgb", "synthetic", args.max_frames
    )
    if not synth_images:
        print("Error: No synthetic images found.", file=sys.stderr)
        sys.exit(1)

    if args.real_dir:
        real_label = args.real_name
        real_images = load_images_from_dir(args.real_dir, real_label, args.max_frames)
        print(f"Real source: {args.real_dir} (label: '{real_label}')")
    else:
        real_label = args.real_name
        print(f"Real Scene ID: {args.scene_id} (label: '{real_label}')")
        print("Error: DB mode not available (PostgreSQL is down). Use --real-dir instead.", file=sys.stderr)
        sys.exit(1)

    if not real_images:
        print("Error: No real images found.", file=sys.stderr)
        sys.exit(1)

    print(f"\nSynthetic frames: {len(synth_images)}")
    print(f"Real frames: {len(real_images)}")
    print(f"Modes: {', '.join(args.modes)}")

    synth_label = "synthetic"
    results = []
    for mode in args.modes:
        print(f"\n--- Mode: {mode} ---")
        results.append(evaluate_domain(synth_label, synth_images, synth_label, synth_images, mode, args.max_frames))
        results.append(evaluate_domain(real_label, real_images, real_label, real_images, mode, args.max_frames))
        results.append(evaluate_domain(synth_label, synth_images, real_label, real_images, mode, args.max_frames))
        results.append(evaluate_domain(real_label, real_images, synth_label, synth_images, mode, args.max_frames))

    report = {
        "schema_version": "synth_to_real_transfer.v1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "synthetic_aoi_id": args.aoi_id,
        "real_label": real_label,
        "real_source": str(args.real_dir) if args.real_dir else args.scene_id,
        "synthetic_frame_count": len(synth_images),
        "real_frame_count": len(real_images),
        "modes": args.modes,
        "results": results,
        "summary": {},
    }

    for mode in args.modes:
        mode_r = [r for r in results if r["mode"] == mode]
        synth_self = next((r for r in mode_r if r["domain_pair"] == f"{synth_label}->{synth_label}"), None)
        real_self = next((r for r in mode_r if r["domain_pair"] == f"{real_label}->{real_label}"), None)
        synth_to_real = next((r for r in mode_r if r["domain_pair"] == f"{synth_label}->{real_label}"), None)
        real_to_synth = next((r for r in mode_r if r["domain_pair"] == f"{real_label}->{synth_label}"), None)

        if synth_to_real and real_to_synth and synth_self and real_self:
            cross = (synth_to_real["inlier_ratio"]["mean"] + real_to_synth["inlier_ratio"]["mean"]) / 2
            within = (synth_self["inlier_ratio"]["mean"] + real_self["inlier_ratio"]["mean"]) / 2
            report["summary"][mode] = {
                "within_domain_mean_inlier_ratio": within,
                "cross_domain_mean_inlier_ratio": cross,
                "transfer_gap": within - cross if within > 0 else None,
                f"{synth_label}_self_inlier_ratio": synth_self["inlier_ratio"]["mean"],
                f"{real_label}_self_inlier_ratio": real_self["inlier_ratio"]["mean"],
                f"{synth_label}_to_{real_label}_inlier_ratio": synth_to_real["inlier_ratio"]["mean"],
                f"{real_label}_to_{synth_label}_inlier_ratio": real_to_synth["inlier_ratio"]["mean"],
            }

    output_path = args.output or (aoi_dir / "eval" / "transfer_check.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print(f"\n{'='*60}")
    print(f"Report saved to: {output_path}")
    print(f"{'='*60}")
    if report["summary"]:
        print(json.dumps(report["summary"], indent=2))
    print(f"\nInterpretation:")
    print(f"  Transfer gap = within-domain inlier ratio - cross-domain inlier ratio")
    print(f"  Gap near 0: synthetic and real features behave similarly (good transfer)")
    print(f"  Gap > 0.3: significant domain shift (synthetic textures may not represent reality)")
    print(f"  NOTE: This comparison is most meaningful when synthetic and real images")
    print(f"  depict the SAME physical location. Unrelated scenes will naturally show a large gap.")


if __name__ == "__main__":
    main()
