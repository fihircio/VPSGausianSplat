"""Procedural synthetic renderer for Google 3D AOIs.

Projects 3D geometric streets and buildings onto the camera frame.
Ensures clean, deterministic visual features (grids, windows, bricks)
so that ORB/SIFT/DISK feature extractors can run baseline evaluations.
"""
from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from backend.services.google3d.aoi import AOI
from backend.services.google3d.camera_paths import CameraPathConfig, CameraPose


class ProceduralRenderer:
    def __init__(self, aoi: AOI, config: CameraPathConfig | None = None):
        self.aoi = aoi
        self.config = config or CameraPathConfig()
        self.width = self.config.width
        self.height = self.config.height
        
        # Setup camera intrinsics matrix K
        intr = self.config.intrinsics()
        self.K = np.array([
            [intr["fx"], 0.0, intr["cx"]],
            [0.0, intr["fy"], intr["cy"]],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)
        
        # Deterministically seed the environment generation based on the AOI id and seed
        random_state = random.Random(self.config.seed + hash(self.aoi.aoi_id) % 1000)
        self.buildings = self._generate_buildings(random_state)

    def _generate_buildings(self, rng: random.Random) -> list[dict[str, Any]]:
        """Procedurally generate 3D buildings (boxes) along the AOI polygon."""
        # Find the boundary of the AOI polygon in ENU coordinates
        from backend.services.google3d.transforms import wgs84_to_enu
        polygon_enu = [wgs84_to_enu(p, self.aoi.origin_wgs84) for p in self.aoi.polygon_wgs84]
        
        min_e = min(p.e for p in polygon_enu)
        max_e = max(p.e for p in polygon_enu)
        min_n = min(p.n for p in polygon_enu)
        max_n = max(p.n for p in polygon_enu)
        
        buildings = []
        # Place buildings along the boundaries of the scene
        # We place boxes just outside/inside the sidewalk path to simulate building facades
        num_buildings = 16
        for i in range(num_buildings):
            # Place buildings in a loop around the perimeter
            fraction = i / num_buildings
            # Determine perimeter coordinate
            if fraction < 0.25:
                e = min_e + (max_e - min_e) * (fraction * 4)
                n = min_n - rng.uniform(5.0, 15.0)
            elif fraction < 0.5:
                e = max_e + rng.uniform(5.0, 15.0)
                n = min_n + (max_n - min_n) * ((fraction - 0.25) * 4)
            elif fraction < 0.75:
                e = max_e - (max_e - min_e) * ((fraction - 0.5) * 4)
                n = max_n + rng.uniform(5.0, 15.0)
            else:
                e = min_e - rng.uniform(5.0, 15.0)
                n = max_n - (max_n - min_n) * ((fraction - 0.75) * 4)
                
            w = rng.uniform(10.0, 25.0)  # width (East)
            d = rng.uniform(10.0, 25.0)  # depth (North)
            h = rng.uniform(15.0, 45.0)  # height (Up)
            
            # Color palette (harmonious dark/light slate/bricks)
            hue = rng.randint(0, 180)
            sat = rng.randint(20, 80)
            val = rng.randint(100, 200)
            base_color_hsv = np.uint8([[[hue, sat, val]]])
            base_color_bgr = cv2.cvtColor(base_color_hsv, cv2.COLOR_HSV2BGR)[0, 0].tolist()
            
            buildings.append({
                "center": (e, n),
                "size": (w, d, h),
                "color": base_color_bgr,
                "window_rows": rng.randint(3, 6),
                "window_cols": rng.randint(3, 5),
            })
            
        return buildings

    def _make_camera_matrix(self, pose: CameraPose) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Build camera extrinsics R (world->cam) and t, plus cam_pos."""
        cam_pos = np.array([pose.position_enu.e, pose.position_enu.n, pose.position_enu.u], dtype=np.float32)
        yaw_rad = math.radians(pose.yaw_degrees)
        pitch_rad = math.radians(pose.pitch_degrees)

        z_c = np.array([
            math.sin(yaw_rad) * math.cos(pitch_rad),
            math.cos(yaw_rad) * math.cos(pitch_rad),
            math.sin(pitch_rad)
        ], dtype=np.float32)
        z_c /= np.linalg.norm(z_c)
        x_c = np.array([math.cos(yaw_rad), -math.sin(yaw_rad), 0.0], dtype=np.float32)
        x_c /= np.linalg.norm(x_c)
        y_c = np.cross(z_c, x_c)
        y_c /= np.linalg.norm(y_c)

        R_c_w = np.vstack([x_c, y_c, z_c])
        t_c_w = -R_c_w @ cam_pos
        return R_c_w, t_c_w, cam_pos

    def render(self, pose: CameraPose, draw_depth: bool = False) -> tuple[np.ndarray, np.ndarray | None]:
        """Fast painter's-algorithm render — no per-pixel z-buffer loops."""
        R, t, cam_pos = self._make_camera_matrix(pose)

        rgb = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        pitch_rad = math.radians(pose.pitch_degrees)
        horizon_y = int(self.height / 2.0 + pitch_rad * self.K[1, 1])
        rgb[:max(0, horizon_y), :] = [210, 180, 140]
        rgb[max(0, horizon_y):, :] = [80, 80, 80]

        # Ground grid (OpenCV lines, fast)
        self._render_ground_grid_fast(rgb, R, t, cam_pos)

        # Back-to-front sort, then draw each building face with cv2.fillPoly
        sorted_blds = sorted(
            self.buildings,
            key=lambda b: math.hypot(b["center"][0] - cam_pos[0], b["center"][1] - cam_pos[1]),
            reverse=True,
        )
        for b in sorted_blds:
            self._draw_building_fast(rgb, b, R, t)

        if self.config.jitter_m > 0:
            noise = np.random.normal(0, 3, rgb.shape).astype(np.int16)
            rgb = np.clip(rgb.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        return rgb, (np.zeros((self.height, self.width), dtype=np.float32) if draw_depth else None)

    def _project(self, pts_3d: np.ndarray, R: np.ndarray, t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Project Nx3 ENU points to 2D image coordinates. Returns (pts_2d, z_cam)."""
        pts_cam = (R @ pts_3d.T).T + t
        valid = pts_cam[:, 2] > 0.1
        pts_img = np.zeros((len(pts_3d), 2), dtype=np.float32)
        if np.any(valid):
            projected = (self.K @ pts_cam[valid].T).T
            pts_img[valid] = projected[:, :2] / pts_cam[valid, 2:3]
        return pts_img, pts_cam[:, 2]

    def _render_ground_grid_fast(self, rgb: np.ndarray, R: np.ndarray, t: np.ndarray, cam_pos: np.ndarray):
        """Line-based ground grid using OpenCV drawing primitives."""
        grid_spacing = 5.0
        grid_extent = 100.0
        start_e = math.floor((cam_pos[0] - grid_extent) / grid_spacing) * grid_spacing
        end_e = math.ceil((cam_pos[0] + grid_extent) / grid_spacing) * grid_spacing
        start_n = math.floor((cam_pos[1] - grid_extent) / grid_spacing) * grid_spacing
        end_n = math.ceil((cam_pos[1] + grid_extent) / grid_spacing) * grid_spacing

        for n in np.arange(start_n, end_n, grid_spacing):
            p = np.array([[start_e, n, 0.0], [end_e, n, 0.0]], dtype=np.float32)
            p2d, z = self._project(p, R, t)
            if z[0] > 0.1 and z[1] > 0.1:
                cv2.line(rgb, tuple(p2d[0].astype(int)), tuple(p2d[1].astype(int)), (100, 100, 100), 1, cv2.LINE_AA)
        for e in np.arange(start_e, end_e, grid_spacing):
            p = np.array([[e, start_n, 0.0], [e, end_n, 0.0]], dtype=np.float32)
            p2d, z = self._project(p, R, t)
            if z[0] > 0.1 and z[1] > 0.1:
                cv2.line(rgb, tuple(p2d[0].astype(int)), tuple(p2d[1].astype(int)), (100, 100, 100), 1, cv2.LINE_AA)

    def _build_corners(self, b: dict) -> np.ndarray:
        """Return 8x3 corner array for a building box."""
        e, n = b["center"]
        w, d, h = b["size"]
        hw, hd = w / 2.0, d / 2.0
        return np.array([
            [e - hw, n - hd, 0.0], [e + hw, n - hd, 0.0],
            [e + hw, n + hd, 0.0], [e - hw, n + hd, 0.0],
            [e - hw, n - hd, h],   [e + hw, n - hd, h],
            [e + hw, n + hd, h],   [e - hw, n + hd, h],
        ], dtype=np.float32)

    def _draw_building_fast(self, rgb: np.ndarray, b: dict, R: np.ndarray, t: np.ndarray):
        """Draw building faces + windows using painter's algorithm (no per-pixel loops)."""
        corners_3d = self._build_corners(b)
        corners_2d, corner_z = self._project(corners_3d, R, t)
        cam_pos = -np.linalg.inv(R) @ t
        dist_to_cam = np.linalg.norm(np.mean(corners_3d, axis=0) - cam_pos)
        skip_windows = dist_to_cam > 120.0

        faces = [
            ([0, 1, 5, 4], np.array([0.0, -1.0, 0.0])),
            ([1, 2, 6, 5], np.array([1.0, 0.0, 0.0])),
            ([2, 3, 7, 6], np.array([0.0, 1.0, 0.0])),
            ([3, 0, 4, 7], np.array([-1.0, 0.0, 0.0])),
            ([4, 5, 6, 7], np.array([0.0, 0.0, 1.0])),
        ]
        light_dir = np.array([0.5, -0.5, 0.7], dtype=np.float32)
        light_dir /= np.linalg.norm(light_dir)

        for idx, normal in faces:
            f_z = corner_z[idx]
            if np.any(f_z <= 0.1):
                continue

            face_center_enu = np.mean(corners_3d[idx], axis=0)
            cam_pos = -np.linalg.inv(R) @ t
            to_face = face_center_enu - cam_pos
            to_face_norm = np.linalg.norm(to_face)
            if to_face_norm == 0:
                continue
            to_face /= to_face_norm
            if np.dot(to_face, normal) > 0.0:
                continue

            pts = corners_2d[idx].astype(np.int32)
            cos_theta = np.dot(normal, light_dir)
            shading = 0.5 + 0.5 * max(0.0, cos_theta)
            color = [int(max(0, min(255, c * shading))) for c in b["color"]]
            cv2.fillPoly(rgb, [pts], color)

            # Windows: skip roof and distant buildings
            if normal[2] < 0.9 and not skip_windows:
                self._draw_windows_fast(rgb, b, idx, corners_3d, R, t)

    def _draw_windows_fast(self, rgb: np.ndarray, b: dict, face_idx: list[int],
                           corners_3d: np.ndarray, R: np.ndarray, t: np.ndarray):
        """Draw window grid on a face using cv2.fillPoly — no per-pixel loops."""
        p0, p1, p2, p3 = corners_3d[face_idx]
        rows, cols = b["window_rows"], b["window_cols"]
        uv = np.array([(0, 0), (1, 0), (1, 1), (0, 1)], dtype=np.float32)

        for r in range(rows):
            for c in range(cols):
                r0, r1 = (r + 0.2) / rows, (r + 0.8) / rows
                c0, c1 = (c + 0.2) / cols, (c + 0.8) / cols
                # Compute 4 window corners via bilinear interpolation
                pts_3d = np.array([
                    (1-u)*(1-v)*p0 + u*(1-v)*p1 + u*v*p2 + (1-u)*v*p3
                    for (u, v) in [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]
                ], dtype=np.float32)
                pts_2d, win_z = self._project(pts_3d, R, t)
                if np.any(win_z <= 0.1):
                    continue
                cv2.fillPoly(rgb, [pts_2d.astype(np.int32)], (50, 40, 20))
