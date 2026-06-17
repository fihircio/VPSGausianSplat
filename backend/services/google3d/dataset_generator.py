"""COLMAP-ready dataset generator from Blender renders.

Reads rendered images and camera poses produced by the Blender mesh renderer,
then writes:

- ``cameras.txt``   — pinhole intrinsic model
- ``images.txt``    — pose per image (quaternion + translation)
- ``points3D.txt``  — empty (no SfM points in synthetic data)
- ``dataset.json``  — structured metadata for training pipelines

Supports deterministic train / val / test splitting.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import numpy as np

from backend.utils.config import get_settings


def _parse_poses_txt(poses_path: Path) -> list[dict[str, Any]]:
    """Parse a COLMAP-style ``poses.txt`` file.

    Returns a list of dicts with keys: *image_id*, *qw*, *qx*, *qy*, *qz*,
    *tx*, *ty*, *tz*, *camera_id*, *image_name*.
    """
    records: list[dict[str, Any]] = []
    with poses_path.open("r", encoding="utf-8") as fh:
        lines = fh.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        # Image lines have at least 10 tokens: ID, QW, QX, QY, QZ, TX, TY, TZ, CAM_ID, NAME
        if len(parts) < 10:
            continue
        record = {
            "image_id": int(parts[0]),
            "qw": float(parts[1]),
            "qx": float(parts[2]),
            "qy": float(parts[3]),
            "qz": float(parts[4]),
            "tx": float(parts[5]),
            "ty": float(parts[6]),
            "tz": float(parts[7]),
            "camera_id": int(parts[8]),
            "image_name": parts[9],
        }
        records.append(record)
    return records


def _split_indices(
    n: int,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42,
) -> dict[str, list[int]]:
    """Deterministically partition *n* indices into train/val/test sets."""
    assert abs(train_ratio + val_ratio - 1.0) <= 1e-9 or train_ratio + val_ratio < 1.0
    test_ratio = 1.0 - train_ratio - val_ratio
    rng = random.Random(seed)
    indices = list(range(n))
    rng.shuffle(indices)

    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    return {
        "train": sorted(indices[:n_train]),
        "val": sorted(indices[n_train:n_train + n_val]),
        "test": sorted(indices[n_train + n_val:]),
    }


def generate_dataset(
    aoi_name: str,
    renders_dir: Path | None = None,
    output_dir: Path | None = None,
    split: tuple[float, float, float] = (0.8, 0.1, 0.1),
    seed: int = 42,
) -> dict[str, Any]:
    """Read rendered images + poses and produce COLMAP dataset files.

    Parameters
    ----------
    aoi_name : str
        AOI identifier used to locate renders under
        ``storage/google3d/{aoi_name}/renders/``.
    renders_dir : Path, optional
        Override the renders directory.  Defaults to
        ``storage/google3d/{aoi_name}/renders/``.
    output_dir : Path, optional
        Where to write COLMAP files.  Defaults to *renders_dir*.
    split : tuple
        (train, val, test) ratios.  Must sum to 1.0.
    seed : int
        Random seed for reproducible splits.

    Returns
    -------
    dict
        Dataset summary manifest (paths, counts, intrinsics).
    """
    storage_root = get_settings().storage_root / "google3d"
    if renders_dir is None:
        renders_dir = storage_root / aoi_name / "renders"
    if output_dir is None:
        output_dir = renders_dir

    renders_dir = Path(renders_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Read poses
    # ------------------------------------------------------------------
    poses_path = renders_dir / "poses.txt"
    if not poses_path.exists():
        raise FileNotFoundError(f"poses.txt not found at {poses_path}")

    records = _parse_poses_txt(poses_path)
    if not records:
        raise ValueError(f"No valid pose records found in {poses_path}")

    # Verify render files exist
    for rec in records:
        img_path = renders_dir / "rgb" / rec["image_name"]
        if not img_path.exists():
            raise FileNotFoundError(f"Rendered image not found: {img_path}")

    # ------------------------------------------------------------------
    # 2. Intrinsics — read from first pose line or default
    # ------------------------------------------------------------------
    camera_model = "PINHOLE"
    width = 640
    height = 480
    fx = 500.0
    fy = 500.0
    cx = width / 2.0
    cy = height / 2.0

    # Try to pull intrinsics from a nearby trajectory.json
    trajectory_path = storage_root / aoi_name / "render_runs" / "scaffold" / "trajectory.json"
    if trajectory_path.exists():
        try:
            with trajectory_path.open("r", encoding="utf-8") as fh:
                traj = json.load(fh)
            if traj.get("frames"):
                intr = traj["frames"][0].get("intrinsics", {})
                width = int(intr.get("width", width))
                height = int(intr.get("height", height))
                fx = float(intr.get("fx", fx))
                fy = float(intr.get("fy", fy))
                cx = float(intr.get("cx", cx))
                cy = float(intr.get("cy", cy))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 3. Write COLMAP cameras.txt
    # ------------------------------------------------------------------
    cam_lines = [
        "# Camera list with one line of data per camera:",
        "#   CAMERA_ID MODEL WIDTH HEIGHT PARAMS[]",
        f"1 {camera_model} {width} {height} {fx:.10f} {fy:.10f} {cx:.10f} {cy:.10f}",
        "",
    ]
    cameras_path = output_dir / "cameras.txt"
    with cameras_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(cam_lines))

    # ------------------------------------------------------------------
    # 4. Write COLMAP images.txt
    # ------------------------------------------------------------------
    img_lines = [
        "# Image list with two lines of data per image:",
        "#   IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID IMAGE_NAME",
        "#   POINTS2D[] as X Y POINT3D_ID",
        "",
    ]
    for rec in records:
        img_lines.append(
            f"{rec['image_id']} {rec['qw']:.10f} {rec['qx']:.10f} {rec['qy']:.10f} "
            f"{rec['qz']:.10f} {rec['tx']:.6f} {rec['ty']:.6f} {rec['tz']:.6f} "
            f"{rec['camera_id']} {rec['image_name']}"
        )
        # No 2D-3D correspondences — empty line
        img_lines.append("")

    images_path = output_dir / "images.txt"
    with images_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(img_lines))

    # ------------------------------------------------------------------
    # 5. Write empty points3D.txt
    # ------------------------------------------------------------------
    points3d_lines = [
        "# 3D point list with one line of data per point:",
        "#   POINT3D_ID X Y Z R G B ERR TRACK[] as IMAGE_ID POINT2D_IDX",
        "",
    ]
    points3d_path = output_dir / "points3D.txt"
    with points3d_path.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(points3d_lines))

    # ------------------------------------------------------------------
    # 6. Dataset splits
    # ------------------------------------------------------------------
    train_ratio, val_ratio, test_ratio = split
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-9, \
        f"Split ratios must sum to 1.0, got {split}"
    splits = _split_indices(len(records), train_ratio, val_ratio, seed)

    # ------------------------------------------------------------------
    # 7. Write dataset.json
    # ------------------------------------------------------------------
    dataset = {
        "schema_version": "google3d.dataset.v1",
        "aoi_name": aoi_name,
        "camera_model": camera_model,
        "intrinsics": {
            "width": width,
            "height": height,
            "fx": fx,
            "fy": fy,
            "cx": cx,
            "cy": cy,
        },
        "num_images": len(records),
        "renders_dir": str(renders_dir.resolve()),
        "images_dir": str((renders_dir / "rgb").resolve()),
        "depth_dir": str((renders_dir / "depth").resolve()) if (renders_dir / "depth").exists() else None,
        "poses_path": str(poses_path.resolve()),
        "colmap_files": {
            "cameras": str(cameras_path.resolve()),
            "images": str(images_path.resolve()),
            "points3D": str(points3d_path.resolve()),
        },
        "splits": {
            split_name: [
                {
                    "image_id": records[i]["image_id"],
                    "image_name": records[i]["image_name"],
                    "image_path": str((renders_dir / "rgb" / records[i]["image_name"]).resolve()),
                }
                for i in indices
            ]
            for split_name, indices in splits.items()
        },
        "split_ratios": {
            "train": train_ratio,
            "val": val_ratio,
            "test": test_ratio,
        },
        "all_frames": [
            {
                "image_id": rec["image_id"],
                "image_name": rec["image_name"],
                "qw": rec["qw"],
                "qx": rec["qx"],
                "qy": rec["qy"],
                "qz": rec["qz"],
                "tx": rec["tx"],
                "ty": rec["ty"],
                "tz": rec["tz"],
            }
            for rec in records
        ],
    }

    dataset_path = output_dir / "dataset.json"
    with dataset_path.open("w", encoding="utf-8") as fh:
        json.dump(dataset, fh, indent=2)

    return dataset


def read_dataset(dataset_path: Path) -> dict[str, Any]:
    """Load a previously generated ``dataset.json``."""
    with dataset_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)
