"""Blender headless mesh renderer for Google 3D scenes.

Generates an inline Blender Python script that:
  1. Imports *scene.glb*
  2. Sets up an Eevee renderer
  3. Places a camera at each pose from the AOI trajectory
  4. Renders RGB (and optional depth) frames
  5. Writes ``poses.txt`` in COLMAP format

The renderer is invoked via ``subprocess.run(["blender", "-b", "-P", script, ...])``.
"""

from __future__ import annotations

import json
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from backend.utils.config import get_settings

_BLENDER_SCRIPT_TEMPLATE = r'''
"""Auto-generated Blender render worker for Google 3D dataset."""
import argparse
import json
import math
import struct
import sys
from pathlib import Path

import bpy
import mathutils
import numpy as np


# ---------------------------------------------------------------------------
# COLMAP format helpers
# ---------------------------------------------------------------------------

def _rot_to_quat(R: np.ndarray) -> tuple[float, float, float, float]:
    """Convert 3x3 rotation matrix to (qw, qx, qy, qz)."""
    trace = R[0, 0] + R[1, 1] + R[2, 2]
    if trace > 0.0:
        s = 0.5 / math.sqrt(trace + 1.0)
        qw = 0.25 / s
        qx = (R[2, 1] - R[1, 2]) * s
        qy = (R[0, 2] - R[2, 0]) * s
        qz = (R[1, 0] - R[0, 1]) * s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = 2.0 * math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        qw = (R[2, 1] - R[1, 2]) / s
        qx = 0.25 * s
        qy = (R[0, 1] + R[1, 0]) / s
        qz = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = 2.0 * math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        qw = (R[0, 2] - R[2, 0]) / s
        qx = (R[0, 1] + R[1, 0]) / s
        qy = 0.25 * s
        qz = (R[1, 2] + R[2, 1]) / s
    else:
        s = 2.0 * math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        qw = (R[1, 0] - R[0, 1]) / s
        qx = (R[0, 2] + R[2, 0]) / s
        qy = (R[1, 2] + R[2, 1]) / s
        qz = 0.25 * s
    return (qw, qx, qy, qz)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

argv = sys.argv
sep_idx = argv.index("--") if "--" in argv else len(argv)
args_list = argv[sep_idx + 1:] if sep_idx < len(argv) else []

parser = argparse.ArgumentParser()
parser.add_argument("--scene", required=True)
parser.add_argument("--poses", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--depth", action="store_true", default=False)
parsed = parser.parse_args(args_list)

scene_path = Path(parsed.scene)
poses_path = Path(parsed.poses)
output_dir = Path(parsed.output)
output_dir.mkdir(parents=True, exist_ok=True)
render_depth = parsed.depth

# ---------------------------------------------------------------------------
# Clear default scene & import GLB
# ---------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)

bpy.ops.import_scene.gltf(filepath=str(scene_path.resolve()))

# Scene bounds (for compositor Z pass setup)
scene = bpy.context.scene

# ---------------------------------------------------------------------------
# Render engine setup (Eevee)
# ---------------------------------------------------------------------------
scene.render.engine = "BLENDER_EEVEE"
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.resolution_percentage = 100
scene.render.use_compositing = False
scene.render.use_freestyle = False

# Transparent film so we can composite later if needed
scene.render.film_transparent = False

# ---------------------------------------------------------------------------
# Load camera poses
# ---------------------------------------------------------------------------
with poses_path.open("r", encoding="utf-8") as fh:
    poses_data = json.load(fh)

frames = poses_data.get("frames", [])
if not frames:
    raise ValueError("No frames found in poses JSON")

# Take intrinsics from first frame (all frames share the same camera)
first = frames[0]
intr = first["intrinsics"]
width = int(intr["width"])
height = int(intr["height"])
fx = float(intr["fx"])
fy = float(intr.get("fy", fx))
cx = float(intr.get("cx", width / 2.0))
cy = float(intr.get("cy", height / 2.0))

scene.render.resolution_x = width
scene.render.resolution_y = height

# ---------------------------------------------------------------------------
# Create camera object
# ---------------------------------------------------------------------------
cam_data = bpy.data.cameras.new("RenderCam")
cam_data.sensor_fit = "AUTO"
cam_data.lens = fx / max(width, height) * 36.0  # approximate 35mm sensor
cam_data.sensor_width = 36.0
cam_data.sensor_height = 24.0
cam_obj = bpy.data.objects.new("RenderCam", cam_data)
bpy.context.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

# ---------------------------------------------------------------------------
# COLMAP poses output
# ---------------------------------------------------------------------------
poses_lines = []
poses_lines.append("# Camera list with one line of data per camera:")
poses_lines.append(f"#   CAMERA_ID MODEL WIDTH HEIGHT PARAMS[]")
poses_lines.append(f"1 PINHOLE {width} {height} {fx:.6f} {fy:.6f} {cx:.6f} {cy:.6f}")
poses_lines.append("")
poses_lines.append("# Image list with two lines of data per image:")
poses_lines.append("#   IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID IMAGE_NAME")
poses_lines.append("#   POINTS2D[]")
poses_lines.append("")
poses_lines.append("# 3D point list (empty):")
poses_lines.append("#   POINT3D_ID X Y Z R G B ERR TRACK[]")
poses_lines.append("")

# ---------------------------------------------------------------------------
# Render loop
# ---------------------------------------------------------------------------
render_dir_rgb = output_dir / "rgb"
render_dir_rgb.mkdir(parents=True, exist_ok=True)

if render_depth:
    _setup_depth_compositor(scene, output_dir)

for frame_idx, frame_data in enumerate(frames):
    frame_id = frame_data.get("frame_id", f"frame_{frame_idx:06d}")
    pos_enu = frame_data["position_enu"]
    yaw_deg = float(frame_data["rotation_ypr_degrees_enu"]["yaw"])
    pitch_deg = float(frame_data["rotation_ypr_degrees_enu"]["pitch"])
    roll_deg = float(frame_data["rotation_ypr_degrees_enu"].get("roll", 0.0))

    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)

    cam_pos = np.array([pos_enu[0], pos_enu[1], pos_enu[2]], dtype=np.float64)

    # Camera axes in world (ENU) frame  —  matches rendering.Renderer._make_camera_matrix
    z_c = np.array([
        math.sin(yaw) * math.cos(pitch),
        math.cos(yaw) * math.cos(pitch),
        math.sin(pitch),
    ], dtype=np.float64)
    norm_z = np.linalg.norm(z_c)
    if norm_z > 1e-12:
        z_c /= norm_z
    x_c = np.array([math.cos(yaw), -math.sin(yaw), 0.0], dtype=np.float64)
    norm_x = np.linalg.norm(x_c)
    if norm_x > 1e-12:
        x_c /= norm_x
    y_c = np.cross(z_c, x_c)
    norm_y = np.linalg.norm(y_c)
    if norm_y > 1e-12:
        y_c /= norm_y

    # Blender camera matrix_world (column-major):
    #   Col 0: local X in world (camera right)
    #   Col 1: local Y in world (camera up)
    #   Col 2: local Z in world (camera backward = -forward)
    #   Col 3: translation (camera position)
    mat = mathutils.Matrix((
        (x_c[0], y_c[0], -z_c[0], cam_pos[0]),
        (x_c[1], y_c[1], -z_c[1], cam_pos[1]),
        (x_c[2], y_c[2], -z_c[2], cam_pos[2]),
        (0.0, 0.0, 0.0, 1.0),
    ))
    cam_obj.matrix_world = mat

    # Render
    rgb_path = str(render_dir_rgb / f"{frame_id}.png")

    # Set output path via filepath — scene.render.filepath includes frame number by default
    scene.render.filepath = rgb_path
    bpy.ops.render.render(write_still=True)

    # Write COLMAP pose entry
    R_c_w = np.vstack([x_c, y_c, z_c])
    qw, qx, qy, qz = _rot_to_quat(R_c_w)
    tx, ty, tz = float(cam_pos[0]), float(cam_pos[1]), float(cam_pos[2])

    poses_lines.append(f"{frame_idx + 1} {qw:.10f} {qx:.10f} {qy:.10f} {qz:.10f} {tx:.6f} {ty:.6f} {tz:.6f} 1 {frame_id}.png")
    poses_lines.append("")

# Write poses.txt
poses_path_out = output_dir / "poses.txt"
with poses_path_out.open("w", encoding="utf-8") as fh:
    fh.write("\n".join(poses_lines))

print(f"[Blender Renderer] Done. {len(frames)} frames rendered to {output_dir}")
'''


def _setup_depth_compositor(scene: Any, output_dir: Path) -> None:
    """Configure Blender compositor to output linear depth as EXR."""
    depth_dir = output_dir / "depth"
    depth_dir.mkdir(parents=True, exist_ok=True)

    scene.use_nodes = True
    tree = scene.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    rl = nodes.new("CompositorNodeRLayers")
    rl.location = (0, 0)

    depth_file = nodes.new("CompositorNodeOutputFile")
    depth_file.location = (300, 0)
    depth_file.format.file_format = "OPEN_EXR"
    depth_file.format.color_depth = "32"
    depth_file.base_path = str(depth_dir.resolve())

    # Map socket names — Eevee outputs 'Depth' from render layers
    try:
        links.new(rl.outputs["Depth"], depth_file.inputs[0])
    except KeyError:
        print("[WARN] Depth pass not available in Eevee; skipping depth output.")


def generate_render_script(scene_glb_path: Path, poses_json_path: Path,
                           output_dir: Path, render_depth: bool = False) -> str:
    """Generate the Blender Python render script and return the file path."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(_BLENDER_SCRIPT_TEMPLATE)
        return fh.name


def run_blender(
    scene_glb_path: Path,
    poses_json_path: Path,
    output_dir: Path,
    blender_bin: str | None = None,
    render_depth: bool = False,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    """Invoke Blender headless to render the scene from each camera pose.

    Parameters
    ----------
    scene_glb_path : Path
        Path to the merged ``scene.glb`` produced by :func:`build_scene`.
    poses_json_path : Path
        Path to a JSON file structured like the existing ``trajectory.json``
        (``{"frames": [...]}``) with ``position_enu`` and
        ``rotation_ypr_degrees_enu`` per frame.
    output_dir : Path
        Where to write rendered frames (``rgb/``) and ``poses.txt``.
    blender_bin : str, optional
        Path to the Blender executable.  Defaults to ``"blender"`` (assumed on
        ``PATH``) or the value of ``settings.blender_bin``.
    render_depth : bool, optional
        If *True*, also render a depth pass (OpenEXR).
    capture_output : bool, optional
        If *True*, capture stdout/stderr from the Blender subprocess.

    Returns
    -------
    subprocess.CompletedProcess
    """
    if blender_bin is None:
        blender_bin = getattr(get_settings(), "blender_bin", "blender")

    output_dir.mkdir(parents=True, exist_ok=True)

    script_path = generate_render_script(
        scene_glb_path, poses_json_path, output_dir, render_depth
    )

    cmd = [
        blender_bin,
        "-b",
        "-P", script_path,
        "--",
        "--scene", str(scene_glb_path.resolve()),
        "--poses", str(poses_json_path.resolve()),
        "--output", str(output_dir.resolve()),
    ]
    if render_depth:
        cmd.append("--depth")

    result = subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        timeout=7200,
    )
    return result
