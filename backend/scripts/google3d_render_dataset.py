#!/usr/bin/env python3
"""Render procedurally generated synthetic frames along an AOI camera path."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

from backend.services.google3d.aoi import AOIRegistry
from backend.services.google3d.camera_paths import CameraPathConfig, CameraPose
from backend.services.google3d.rendering import ProceduralRenderer
from backend.services.google3d.transforms import ENUPoint


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="AOI registry JSON config")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("backend/storage/google3d"),
        help="Root folder for Google 3D scaffold output",
    )
    parser.add_argument("--aoi-id", help="AOI ID to render; defaults to the first AOI in config")
    parser.add_argument("--limit", type=int, default=100, help="Maximum number of frames to render")
    parser.add_argument("--depth", action="store_true", help="Also generate depth images")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    
    # Load AOI registry
    if not args.config.exists():
        print(f"Error: Config file {args.config} does not exist", file=sys.stderr)
        sys.exit(1)
        
    registry = AOIRegistry.load(args.config)
    aoi = registry.get(args.aoi_id) if args.aoi_id else registry.aois[0]
    
    aoi_dir = args.output_root / "aois" / aoi.aoi_id
    trajectory_path = aoi_dir / "render_runs" / "scaffold" / "trajectory.json"
    
    if not trajectory_path.exists():
        print(f"Error: Trajectory scaffold not found at {trajectory_path}. Run google3d_ingest_aoi.py first.", file=sys.stderr)
        sys.exit(1)
        
    with open(trajectory_path, "r", encoding="utf-8") as fh:
        trajectory_data = json.load(fh)
        
    frames_data = trajectory_data.get("frames", [])
    if not frames_data:
        print("Error: No frames found in trajectory file.", file=sys.stderr)
        sys.exit(1)
        
    # Create output directories
    rgb_dir = aoi_dir / "render_runs" / "scaffold" / "rgb"
    rgb_dir.mkdir(parents=True, exist_ok=True)
    
    depth_dir = aoi_dir / "render_runs" / "scaffold" / "depth"
    if args.depth:
        depth_dir.mkdir(parents=True, exist_ok=True)
        
    print(f"Rendering synthetic frames for AOI: {aoi.aoi_id}")
    print(f"Output directory: {rgb_dir}")
    
    # Read camera config from first frame or defaults
    camera_config = CameraPathConfig(
        width=frames_data[0]["intrinsics"]["width"],
        height=frames_data[0]["intrinsics"]["height"],
        fov_degrees=frames_data[0]["intrinsics"]["fov_degrees"]
    )
    renderer = ProceduralRenderer(aoi, camera_config)
    
    rendered_count = 0
    limit = min(len(frames_data), args.limit)
    
    for idx in range(limit):
        f = frames_data[idx]
        frame_id = f["frame_id"]
        
        pos_list = f["position_enu"]
        pos_enu = ENUPoint(pos_list[0], pos_list[1], pos_list[2])
        
        rot = f["rotation_ypr_degrees_enu"]
        pose = CameraPose(
            frame_id=frame_id,
            position_enu=pos_enu,
            yaw_degrees=rot["yaw"],
            pitch_degrees=rot["pitch"],
            roll_degrees=rot.get("roll", 0.0)
        )
        
        # Render the frame
        rgb, depth_img = renderer.render(pose, draw_depth=args.depth)
        
        # Save RGB image
        rgb_path = rgb_dir / f"{frame_id}.png"
        cv2.imwrite(str(rgb_path), rgb)
        
        # Save Depth image if requested
        if args.depth and depth_img is not None:
            # Scale depth for visualization/storage (e.g. 16-bit PNG or normalized 8-bit)
            depth_scaled = np.clip(depth_img * 100, 0, 65535).astype(np.uint16)
            depth_path = depth_dir / f"{frame_id}.png"
            cv2.imwrite(str(depth_path), depth_scaled)
            
        rendered_count += 1
        if (idx + 1) % 5 == 0 or idx == limit - 1:
            print(f"Rendered {idx + 1}/{limit} frames...")
            
    print(f"\nSuccessfully rendered {rendered_count} frames to {rgb_dir}")


if __name__ == "__main__":
    main()
