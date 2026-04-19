"""
tile_splat.py — Standalone octree tiling utility for VPSGausianSplat.

Usage:
    python -m backend.scripts.tile_splat --scene-id <UUID>

Reads:
    backend/storage/splats/<scene_id>/sparse_points_fallback.ply

Writes:
    backend/storage/splats/<scene_id>/tiles/tile_manifest.json
    backend/storage/splats/<scene_id>/tiles/tile_<nodeId>.ply

Dependencies:
    numpy, plyfile  (pip install plyfile)

This script is intentionally self-contained — no Celery, no SQLAlchemy.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_POINTS_PER_TILE = 100_000
MIN_LEAF_SIZE = 500  # Don't bother splitting below this many points


# ---------------------------------------------------------------------------
# PLY I/O helpers (pure-numpy, avoids open3d dependency)
# ---------------------------------------------------------------------------

def _read_ply(path: Path) -> np.ndarray:
    """Load PLY into an (N, 3+) structured numpy array via plyfile or manual parse."""
    try:
        from plyfile import PlyData  # type: ignore

        plydata = PlyData.read(str(path))
        el = plydata["vertex"]
        x = el["x"].astype(np.float32)
        y = el["y"].astype(np.float32)
        z = el["z"].astype(np.float32)

        # Try to get colors
        try:
            r = el["red"].astype(np.uint8)
            g = el["green"].astype(np.uint8)
            b = el["blue"].astype(np.uint8)
            pts = np.column_stack([x, y, z, r, g, b])
        except Exception:
            pts = np.column_stack([x, y, z])

        return pts

    except ImportError:
        raise ImportError(
            "plyfile is required: pip install plyfile"
        ) from None


def _write_ply(path: Path, pts: np.ndarray) -> None:
    """Write an (N,3) or (N,6) float32/uint8 array as a PLY point cloud."""
    has_color = pts.shape[1] >= 6
    path.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "ply",
        "format binary_little_endian 1.0",
        f"element vertex {len(pts)}",
        "property float x",
        "property float y",
        "property float z",
    ]
    if has_color:
        header += [
            "property uchar red",
            "property uchar green",
            "property uchar blue",
        ]
    header.append("end_header")
    header_bytes = ("\n".join(header) + "\n").encode("ascii")

    with path.open("wb") as f:
        f.write(header_bytes)
        if has_color:
            xyz = pts[:, :3].astype(np.float32)
            rgb = pts[:, 3:6].astype(np.uint8)
            # Interleave float xyz + uchar rgb per vertex
            for i in range(len(pts)):
                f.write(struct.pack("<fff", xyz[i, 0], xyz[i, 1], xyz[i, 2]))
                f.write(struct.pack("BBB", rgb[i, 0], rgb[i, 1], rgb[i, 2]))
        else:
            pts[:, :3].astype(np.float32).tofile(f)


# ---------------------------------------------------------------------------
# Octree node
# ---------------------------------------------------------------------------

@dataclass
class OctreeNode:
    node_id: str
    depth: int
    bbox_min: list[float]  # [x, y, z]
    bbox_max: list[float]
    point_indices: np.ndarray = field(repr=False)
    children: list["OctreeNode"] = field(default_factory=list)


def _build_octree(
    pts: np.ndarray,
    indices: np.ndarray,
    bbox_min: np.ndarray,
    bbox_max: np.ndarray,
    node_id: str = "root",
    depth: int = 0,
) -> OctreeNode:
    node = OctreeNode(
        node_id=node_id,
        depth=depth,
        bbox_min=bbox_min.tolist(),
        bbox_max=bbox_max.tolist(),
        point_indices=indices,
    )

    n = len(indices)
    if n <= MAX_POINTS_PER_TILE or n <= MIN_LEAF_SIZE:
        return node  # leaf

    # Split at midpoint on each axis
    mid = (bbox_min + bbox_max) / 2.0
    positions = pts[indices, :3]

    child_idx = 0
    for xi in range(2):
        for yi in range(2):
            for zi in range(2):
                mask = (
                    ((positions[:, 0] >= mid[0]) == bool(xi))
                    & ((positions[:, 1] >= mid[1]) == bool(yi))
                    & ((positions[:, 2] >= mid[2]) == bool(zi))
                )
                child_pts = indices[mask]
                if len(child_pts) == 0:
                    child_idx += 1
                    continue

                c_min = np.array([
                    mid[0] if xi else bbox_min[0],
                    mid[1] if yi else bbox_min[1],
                    mid[2] if zi else bbox_min[2],
                ])
                c_max = np.array([
                    bbox_max[0] if xi else mid[0],
                    bbox_max[1] if yi else mid[1],
                    bbox_max[2] if zi else mid[2],
                ])
                child_node = _build_octree(
                    pts, child_pts, c_min, c_max,
                    node_id=f"{node_id}_{child_idx}",
                    depth=depth + 1,
                )
                node.children.append(child_node)
                child_idx += 1

    return node


# ---------------------------------------------------------------------------
# Write tiles and build manifest
# ---------------------------------------------------------------------------

def _collect_leaves(node: OctreeNode, leaves: list[OctreeNode]) -> None:
    if not node.children:
        leaves.append(node)
    else:
        for child in node.children:
            _collect_leaves(child, leaves)


def _node_to_manifest_entry(node: OctreeNode) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "depth": node.depth,
        "bbox_min": node.bbox_min,
        "bbox_max": node.bbox_max,
        "point_count": len(node.point_indices),
        "is_leaf": len(node.children) == 0,
        "children": [c.node_id for c in node.children],
    }


def _flatten_tree(node: OctreeNode) -> list[dict[str, Any]]:
    entries = [_node_to_manifest_entry(node)]
    for child in node.children:
        entries.extend(_flatten_tree(child))
    return entries


# ---------------------------------------------------------------------------
# Main tiling pipeline
# ---------------------------------------------------------------------------

def tile_scene(scene_id: str, storage_root: Path) -> None:
    ply_path = storage_root / "splats" / scene_id / "sparse_points_fallback.ply"
    tiles_dir = storage_root / "splats" / scene_id / "tiles"

    if not ply_path.exists():
        print(f"[tile_splat] ERROR: PLY not found at {ply_path}", file=sys.stderr)
        sys.exit(1)

    t0 = time.perf_counter()
    print(f"[tile_splat] Loading {ply_path} …")
    pts = _read_ply(ply_path)
    n_total = len(pts)
    print(f"[tile_splat] Loaded {n_total:,} points in {time.perf_counter()-t0:.2f}s")

    # Compute global bounding box
    bbox_min = pts[:, :3].min(axis=0)
    bbox_max = pts[:, :3].max(axis=0)
    print(f"[tile_splat] BBox: {bbox_min.tolist()} → {bbox_max.tolist()}")

    # Build octree
    print("[tile_splat] Building octree …")
    t1 = time.perf_counter()
    all_indices = np.arange(n_total, dtype=np.int32)
    root = _build_octree(pts, all_indices, bbox_min, bbox_max)
    print(f"[tile_splat] Octree built in {time.perf_counter()-t1:.2f}s")

    # Collect leaves
    leaves: list[OctreeNode] = []
    _collect_leaves(root, leaves)
    print(f"[tile_splat] {len(leaves)} leaf tiles")

    # Write leaf tiles
    tiles_dir.mkdir(parents=True, exist_ok=True)
    t2 = time.perf_counter()
    for leaf in leaves:
        tile_path = tiles_dir / f"tile_{leaf.node_id}.ply"
        _write_ply(tile_path, pts[leaf.point_indices])

    print(f"[tile_splat] Tiles written in {time.perf_counter()-t2:.2f}s")

    # Write manifest
    manifest = {
        "scene_id": scene_id,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_points": n_total,
        "max_points_per_tile": MAX_POINTS_PER_TILE,
        "bbox_min": bbox_min.tolist(),
        "bbox_max": bbox_max.tolist(),
        "nodes": _flatten_tree(root),
    }
    manifest_path = tiles_dir / "tile_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[tile_splat] Manifest → {manifest_path}")
    print(f"[tile_splat] Done in {time.perf_counter()-t0:.2f}s total.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _default_storage_root() -> Path:
    """Resolve storage root the same way config.py does."""
    return Path(__file__).resolve().parent.parent.parent / "backend" / "storage"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Tile a scene PLY into octree leaf tiles for streaming."
    )
    parser.add_argument("--scene-id", required=True, help="Scene UUID")
    parser.add_argument(
        "--storage-root",
        default=None,
        help="Override storage root (default: auto-detected)",
    )
    args = parser.parse_args()

    root = Path(args.storage_root) if args.storage_root else _default_storage_root()
    tile_scene(args.scene_id, root)
