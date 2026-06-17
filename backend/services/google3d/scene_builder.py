"""Assemble downloaded Google 3D tiles into a unified GLB mesh.

Reads B3DM / GLB files from the tile cache, shifts vertices from the
tile's local frame into the AOI ENU frame, and writes a single merged GLB
that preserves UVs and material IDs per tile.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

import numpy as np

from backend.utils.config import get_settings

# ---------------------------------------------------------------------------
# Minimal GLB writer (pure NumPy + struct, no trimesh dependency needed)
# ---------------------------------------------------------------------------
# GLB (GLTF Binary) structure:
#   - 12-byte header: magic "glTF", version 2, total length
#   - JSON chunk: 8-byte chunk header + minified JSON (padded to 4 bytes)
#   - BIN chunk:   8-byte chunk header + binary buffer data (padded to 4 bytes)
# ---------------------------------------------------------------------------

_GLTF_MAGIC = b"glTF"
_GLTF_VERSION = 2
_CHUNK_TYPE_JSON = 0x4E4F534A
_CHUNK_TYPE_BIN = 0x004E4942
_COMPONENT_BYTE_SIZES = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
_TYPE_SIZES = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}
_TINY_INDEX = 1e-7


def _pad4(length: int) -> int:
    return (length + 3) & ~3


def _build_glb(
    vertices: np.ndarray,
    normals: np.ndarray | None,
    texcoords: np.ndarray | None,
    triangles: np.ndarray,
    material_ids: np.ndarray | None,
) -> bytes:
    """Build a binary GLB from vertex arrays.

    Parameters
    ----------
    vertices : (N, 3) float32
    normals : (N, 3) float32 or None
    texcoords : (N, 2) float32 or None
    triangles : (M, 3) uint32
    material_ids : (M,) int32 or None  — one ID per triangle
    """
    indices = triangles.astype(np.uint32)
    if vertices.dtype != np.float32:
        vertices = vertices.astype(np.float32)
    if normals is not None and normals.dtype != np.float32:
        normals = normals.astype(np.float32)
    if texcoords is not None and texcoords.dtype != np.float32:
        texcoords = texcoords.astype(np.float32)

    bin_parts: list[bytes] = [b""]
    accessors: list[dict[str, Any]] = []
    buffer_views: list[dict[str, Any]] = []
    meshes: list[dict[str, Any]] = []
    primitives: list[dict[str, Any]] = []
    materials: list[dict[str, Any]] = []
    offset = 0

    def _add_view(data: bytes) -> int:
        nonlocal offset
        v = len(buffer_views)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": offset,
            "byteLength": len(data),
        })
        bin_parts.append(data)
        offset += _pad4(len(data))
        return v

    def _add_accessor(view_idx: int, comp_type: int, data_type: str, count: int) -> int:
        accessors.append({
            "bufferView": view_idx,
            "componentType": comp_type,
            "count": count,
            "type": data_type,
        })
        return len(accessors) - 1

    # Positions accessor
    pos_view = _add_view(vertices.tobytes())
    pos_acc = _add_accessor(pos_view, 5126, "VEC3", len(vertices))

    min_pos = vertices.min(axis=0).tolist()
    max_pos = vertices.max(axis=0).tolist()
    accessors[-1]["min"] = min_pos
    accessors[-1]["max"] = max_pos

    # Normals accessor
    norm_acc = -1
    if normals is not None:
        n_view = _add_view(normals.tobytes())
        norm_acc = _add_accessor(n_view, 5126, "VEC3", len(normals))

    # Texcoords accessor
    tc_acc = -1
    if texcoords is not None:
        # Flip V for OpenGL convention (0 at bottom)
        tc = texcoords.copy()
        tc[:, 1] = 1.0 - tc[:, 1]
        tc_view = _add_view(tc.tobytes())
        tc_acc = _add_accessor(tc_view, 5126, "VEC2", len(texcoords))

    # Indices accessor
    idx_view = _add_view(indices.tobytes())
    idx_acc = _add_accessor(idx_view, 5125, "SCALAR", len(indices) * 3)

    # Split triangles by material ID
    if material_ids is not None and len(material_ids) > 0:
        unique_mids = sorted(set(material_ids))
        for mid in unique_mids:
            mask = material_ids == mid
            if not mask.any():
                continue
            sub_indices = indices[mask].copy()
            sub_view = _add_view(sub_indices.tobytes())
            sub_acc = _add_accessor(sub_view, 5125, "SCALAR", len(sub_indices) * 3)

            mat_label = f"tile_{mid}"
            materials.append({
                "name": mat_label,
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.8, 0.8, 0.8, 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.8,
                },
            })
            primitives.append({
                "attributes": {"POSITION": pos_acc},
                "indices": sub_acc,
                "material": len(materials) - 1,
            })
            if norm_acc >= 0:
                primitives[-1]["attributes"]["NORMAL"] = norm_acc
            if tc_acc >= 0:
                primitives[-1]["attributes"]["TEXCOORD_0"] = tc_acc
    else:
        # Single material for all triangles
        materials.append({
            "name": "default",
            "pbrMetallicRoughness": {
                "baseColorFactor": [0.8, 0.8, 0.8, 1.0],
                "metallicFactor": 0.0,
                "roughnessFactor": 0.8,
            },
        })
        primitives.append({
            "attributes": {"POSITION": pos_acc},
            "indices": idx_acc,
            "material": 0,
        })
        if norm_acc >= 0:
            primitives[0]["attributes"]["NORMAL"] = norm_acc
        if tc_acc >= 0:
            primitives[0]["attributes"]["TEXCOORD_0"] = tc_acc

    meshes.append({
        "primitives": primitives,
    })

    # Assemble binary buffer
    raw_bin = b"".join(bin_parts)
    padded_bin = raw_bin + b"\x00" * (_pad4(len(raw_bin)) - len(raw_bin))

    # Build JSON
    json_doc: dict[str, Any] = {
        "asset": {"version": "2.0", "generator": "google3d_scene_builder"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": meshes,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(raw_bin)}],
        "materials": materials,
    }
    json_str = json.dumps(json_doc, separators=(",", ":"))

    # Pad JSON to 4 bytes
    padded_json = json_str.encode("utf-8")
    padded_json += b" " * (_pad4(len(padded_json)) - len(padded_json))

    # GLB header
    total_len = 12 + 8 + len(padded_json) + 8 + len(padded_bin)
    header = struct.pack("<4sII", _GLTF_MAGIC, _GLTF_VERSION, total_len)

    # JSON chunk
    json_chunk = struct.pack("<II", len(padded_json), _CHUNK_TYPE_JSON) + padded_json
    bin_chunk = struct.pack("<II", len(padded_bin), _CHUNK_TYPE_BIN) + padded_bin

    return header + json_chunk + bin_chunk


# ---------------------------------------------------------------------------
# Scene builder
# ---------------------------------------------------------------------------


def _load_glb_arrays(path: Path) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None, np.ndarray, np.ndarray | None]:
    """Load vertex arrays from a GLB file using minimal parsing.

    Handles multiple primitives sharing vertex accessors correctly.
    Returns (vertices, normals, texcoords, triangles, material_ids).
    """
    data = path.read_bytes()
    if len(data) < 12:
        raise ValueError(f"Not a valid GLB: {path}")

    magic, version, total_len = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise ValueError(f"Unsupported GLB format in {path} (magic={magic}, version={version})")

    offset = 12
    json_data: dict[str, Any] = {}
    bin_data = b""

    while offset < len(data):
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk_payload = data[offset:offset + chunk_len]
        offset += _pad4(chunk_len)
        if chunk_type == _CHUNK_TYPE_JSON:
            json_data = json.loads(chunk_payload.decode("utf-8").rstrip(" \n\r"))
        elif chunk_type == _CHUNK_TYPE_BIN:
            bin_data = chunk_payload[:chunk_len]

    if not json_data or not bin_data:
        raise ValueError(f"No JSON or BIN chunk found in {path}")

    buffers = json_data.get("buffers", [])
    buffer_views = json_data.get("bufferViews", [])
    accessors = json_data.get("accessors", [])
    meshes = json_data.get("meshes", [])
    if not meshes:
        raise ValueError(f"No meshes found in {path}")

    # Cache: load each unique accessor once keyed by index
    _acc_cache: dict[int, np.ndarray] = {}

    def _cached_read(idx: int | None) -> np.ndarray | None:
        if idx is None or idx < 0 or idx >= len(accessors):
            return None
        if idx not in _acc_cache:
            _acc_cache[idx] = _read_accessor(idx, accessors, buffer_views, buffers, bin_data)
        return _acc_cache[idx]

    # Collect all primitives with their accessor indices
    primitives_data: list[tuple[int, int | None, int | None, np.ndarray, int]] = []
    # (pos_acc_idx, norm_acc_idx, tc_acc_idx, indices_array, material_id)

    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            pos_idx = prim["attributes"].get("POSITION")
            if pos_idx is None:
                continue
            inds = _cached_read(prim.get("indices"))
            if inds is None:
                continue
            inds = inds.reshape(-1, 3)
            mat_id = prim.get("material", -1)
            primitives_data.append((
                pos_idx,
                prim["attributes"].get("NORMAL"),
                prim["attributes"].get("TEXCOORD_0"),
                inds,
                mat_id,
            ))

    if not primitives_data:
        raise ValueError(f"No primitive data found in {path}")

    # Build unified vertex buffer from unique position accessors
    # Strategy: for each primitive, store the base vertex offset and
    # re-index triangles into a shared vertex array

    # Determine unique position accessors
    unique_pos_accs: dict[int, int] = {}  # accessor_idx -> new_vertex_offset
    pos_buffers: list[np.ndarray] = []
    pos_offset = 0
    for pos_idx, _, _, _, _ in primitives_data:
        if pos_idx not in unique_pos_accs:
            unique_pos_accs[pos_idx] = pos_offset
            pos_buffers.append(_cached_read(pos_idx).reshape(-1, 3))
            pos_offset += pos_buffers[-1].shape[0]

    all_verts = np.concatenate(pos_buffers, axis=0).astype(np.float32)

    # Build normals and texcoords from the same unified vertex buffer
    all_norms: np.ndarray | None = None
    all_tcs: np.ndarray | None = None

    # Check if all primitives share the same normal & texcoord accessor setup
    has_norms = any(p[1] is not None for p in primitives_data)
    has_tcs = any(p[2] is not None for p in primitives_data)

    if has_norms:
        norm_buffers = []
        for pos_idx, norm_idx, _, _, _ in primitives_data:
            if norm_idx is not None:
                nbuf = _cached_read(norm_idx).reshape(-1, 3)
            else:
                nbuf = np.zeros((_cached_read(pos_idx).reshape(-1, 3).shape[0], 3), dtype=np.float32)
            norm_buffers.append(nbuf)
        all_norms = np.concatenate(norm_buffers, axis=0).astype(np.float32)

    if has_tcs:
        tc_buffers = []
        for pos_idx, _, tc_idx, _, _ in primitives_data:
            if tc_idx is not None:
                tbuf = _cached_read(tc_idx).reshape(-1, 2)
            else:
                tbuf = np.zeros((_cached_read(pos_idx).reshape(-1, 3).shape[0], 2), dtype=np.float32)
            tc_buffers.append(tbuf)
        all_tcs = np.concatenate(tc_buffers, axis=0).astype(np.float32)

    # Re-index triangles to the unified vertex buffer
    tris_out: list[np.ndarray] = []
    mats_out: list[np.ndarray] = []
    for pos_idx, _, _, inds, mat_id in primitives_data:
        base = unique_pos_accs[pos_idx]
        tris_out.append((inds + base).astype(np.uint32))
        mats_out.append(np.full(len(inds), mat_id, dtype=np.int32))

    tris = np.concatenate(tris_out, axis=0)
    mats = np.concatenate(mats_out, axis=0)

    return all_verts, all_norms, all_tcs, tris, mats


def _read_accessor(
    acc_idx: int | None,
    accessors: list[dict[str, Any]],
    buffer_views: list[dict[str, Any]],
    buffers: list[dict[str, Any]],
    bin_data: bytes,
) -> np.ndarray | None:
    if acc_idx is None or acc_idx < 0 or acc_idx >= len(accessors):
        return None
    acc = accessors[acc_idx]
    bv = buffer_views[acc["bufferView"]]
    comp_type = acc["componentType"]
    data_type = acc["type"]
    count = acc["count"]

    comp_size = _COMPONENT_BYTE_SIZES.get(comp_type, 4)
    type_size = _TYPE_SIZES.get(data_type, 3)
    byte_stride = bv.get("byteStride", 0)
    elem_size = comp_size * type_size
    if byte_stride == 0:
        byte_stride = elem_size

    byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    dtype = _component_dtype(comp_type)
    raw = bin_data[byte_offset:byte_offset + byte_stride * count]

    arr = np.frombuffer(raw, dtype=dtype, count=count * type_size).reshape(count, type_size)

    if "sparse" in acc:
        raise NotImplementedError("Sparse accessors are not supported")

    return arr


def _component_dtype(comp_type: int) -> np.dtype:
    mapping = {
        5120: np.int8,
        5121: np.uint8,
        5122: np.int16,
        5123: np.uint16,
        5125: np.uint32,
        5126: np.float32,
    }
    return mapping.get(comp_type, np.float32)


def build_scene(
    aoi_name: str,
    tile_dir: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """Load all GLB/B3DM tiles in *tile_dir*, merge into a single GLB, and write it.

    Returns the path to the output GLB file.
    """
    if tile_dir is None:
        tile_dir = (
            get_settings().storage_root / "google3d" / aoi_name / "tiles"
        )

    if output_path is None:
        output_path = (
            get_settings().storage_root / "google3d" / aoi_name / "scene.glb"
        )

    if not tile_dir.is_dir():
        raise FileNotFoundError(f"Tile directory not found: {tile_dir}")

    glb_files = sorted(tile_dir.glob("*.glb"))
    b3dm_files = sorted(tile_dir.glob("*.b3dm"))
    tile_paths = glb_files + b3dm_files

    if not tile_paths:
        raise FileNotFoundError(f"No GLB/B3DM files found in {tile_dir}")

    all_verts: list[np.ndarray] = []
    all_norms: list[np.ndarray] = []
    all_tcs: list[np.ndarray] = []
    all_tris: list[np.ndarray] = []
    all_mats: list[np.ndarray] = []
    vert_offset = 0

    for tp in tile_paths:
        if tp.suffix.lower() == ".b3dm":
            raw = tp.read_bytes()
            glb_data = _extract_glb_from_b3dm(raw)
            if glb_data is None:
                continue
            glb_path = tp.with_suffix(".glb")
            glb_path.write_bytes(glb_data)
            load_path = glb_path
        else:
            load_path = tp

        verts, norms, tcs, tris, mats = _load_glb_arrays(load_path)
        all_verts.append(verts)
        if norms is not None and norms.shape[0] == verts.shape[0]:
            all_norms.append(norms)
        else:
            all_norms.append(np.zeros((0, 3), dtype=np.float32))
        if tcs is not None and tcs.shape[0] == verts.shape[0]:
            all_tcs.append(tcs)
        else:
            all_tcs.append(np.zeros((0, 2), dtype=np.float32))

        # Offset triangle indices
        tris_offset = tris + vert_offset
        all_tris.append(tris_offset)
        all_mats.append(mats)
        vert_offset += verts.shape[0]

    merged_verts = np.concatenate(all_verts, axis=0)
    merged_norms = np.concatenate([n for n in all_norms if n.shape[0] > 0], axis=0) if any(n.shape[0] > 0 for n in all_norms) else None
    merged_tcs = np.concatenate([t for t in all_tcs if t.shape[0] > 0], axis=0) if any(t.shape[0] > 0 for t in all_tcs) else None
    merged_tris = np.concatenate(all_tris, axis=0)
    merged_mats = np.concatenate(all_mats, axis=0)

    if merged_norms is not None and merged_norms.shape[0] != merged_verts.shape[0]:
        merged_norms = None
    if merged_tcs is not None and merged_tcs.shape[0] != merged_verts.shape[0]:
        merged_tcs = None

    glb_bytes = _build_glb(merged_verts, merged_norms, merged_tcs, merged_tris, merged_mats)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(glb_bytes)
    return output_path


def _extract_glb_from_b3dm(data: bytes) -> bytes | None:
    """Extract embedded GLB from a B3DM binary payload."""
    if len(data) < 28:
        return None
    if data[:4] != b"b3dm":
        return None
    (_mag, _ver, _total_len, ft_json_len, ft_bin_len, bt_json_len, bt_bin_len) = struct.unpack_from(
        "<4sIIIIII", data, 0
    )
    header_size = 28
    table_size = ft_json_len + ft_bin_len + bt_json_len + bt_bin_len
    glb_offset = header_size + table_size
    if glb_offset + 4 <= len(data) and data[glb_offset:glb_offset + 4] == b"glTF":
        return data[glb_offset:]
    return None
