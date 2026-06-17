"""Google Photorealistic 3D Tiles downloader.

Fetches tiles for a configurable AOI bounding box using the Maps Tiles API,
caches raw GLB/B3DM payloads, and returns tile metadata.

API entry point (3D Tiles 1.0):
  https://tile.googleapis.com/v1/3dtiles/root.json?key={API_KEY}
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from shapely.geometry import Polygon, box

from backend.utils.config import get_settings

TILES_API_BASE = "https://tile.googleapis.com/v1/3dtiles"
REQUEST_TIMEOUT_S = 60.0
DEFAULT_MAX_TILES = 500


@dataclass
class TileMetadata:
    tile_id: str
    content_uri: str
    bounding_region_deg: tuple[float, float, float, float]  # west, south, east, north
    geometric_error: float = 0.0
    transform: list[float] | None = None  # 4x4 row-major transform matrix


def _bbox_deg_from_region(region: list[float]) -> tuple[float, float, float, float]:
    """Convert a Google 3D Tiles region [w, s, e, n, min_h, max_h] in radians to degrees."""
    return (
        math.degrees(region[0]),
        math.degrees(region[1]),
        math.degrees(region[2]),
        math.degrees(region[3]),
    )


class TileDownloader:
    """Downloads Google Photorealistic 3D Tiles overlapping an AOI bounding box.

    Caches raw payloads at ``backend/storage/google3d/{aoi_name}/tiles/``.
    """

    def __init__(self, aoi_name: str, api_key: str | None = None) -> None:
        self.aoi_name = aoi_name
        self.api_key = api_key or get_settings().google_api_key
        if not self.api_key:
            raise ValueError(
                "Google Maps API key is required. "
                "Set google_api_key in backend/.env or pass api_key explicitly."
            )
        self.http_client = httpx.Client(timeout=REQUEST_TIMEOUT_S)
        self.tiles_cache_dir = (
            get_settings().storage_root
            / "google3d"
            / aoi_name
            / "tiles"
        )
        self.tiles_cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_aoi_tiles(
        self,
        bbox_deg: tuple[float, float, float, float],
        max_tiles: int = DEFAULT_MAX_TILES,
    ) -> list[TileMetadata]:
        """Download all tiles overlapping *bbox_deg* ``(west, south, east, north)``.

        Returns a list of :class:`TileMetadata` for downloaded tiles.
        """
        aoi_poly = box(*bbox_deg)
        root_tileset = self._fetch_root_tileset()
        intersecting: list[TileMetadata] = []
        self._traverse(root_tileset.get("root", {}), aoi_poly, intersecting, max_tiles)

        results: list[TileMetadata] = []
        for meta in intersecting:
            local_path = self._download_tile(meta.content_uri)
            if local_path is not None:
                results.append(meta)

        self._write_source_tiles(results)
        return results

    def close(self) -> None:
        self.http_client.close()

    def __enter__(self) -> TileDownloader:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_root_tileset(self) -> dict[str, Any]:
        url = f"{TILES_API_BASE}/root.json?key={self.api_key}"
        resp = self.http_client.get(url)
        resp.raise_for_status()
        return resp.json()

    def _traverse(
        self,
        node: dict[str, Any],
        aoi_poly: Polygon,
        results: list[TileMetadata],
        max_tiles: int,
    ) -> None:
        if not node or len(results) >= max_tiles:
            return

        bv = node.get("boundingVolume", {})
        if "region" in bv:
            w, s, e, n = _bbox_deg_from_region(bv["region"])
            node_box = box(w, s, e, n)
            if not aoi_poly.intersects(node_box):
                return
        elif "box" in bv:
            # Approximate box as a 2D AABB for intersection test
            center = bv["box"][:3]
            hw, hd = bv["box"][3], bv["box"][7]  # x & y half-extents
            cx_lon, cy_lat = math.degrees(center[0]), math.degrees(center[1])
            lon_hw = math.degrees(hw) / math.cos(math.radians(cy_lat)) if abs(cy_lat) < 89.0 else math.degrees(hw)
            node_box = box(cx_lon - lon_hw, cy_lat - math.degrees(hd),
                           cx_lon + lon_hw, cy_lat + math.degrees(hd))
            if not aoi_poly.intersects(node_box):
                return
        else:
            # No bounding volume means we include it
            pass

        content = node.get("content")
        if content and content.get("uri"):
            tile_id = Path(content["uri"]).stem
            if "region" in bv:
                bbox = _bbox_deg_from_region(bv["region"])
            else:
                bbox = (0.0, 0.0, 0.0, 0.0)
            results.append(TileMetadata(
                tile_id=tile_id,
                content_uri=content["uri"],
                bounding_region_deg=bbox,
                geometric_error=node.get("geometricError", 0.0),
                transform=node.get("transform"),
            ))

        for child in node.get("children", []):
            self._traverse(child, aoi_poly, results, max_tiles)

    def _download_tile(self, content_uri: str) -> Path | None:
        """Download a tile payload (B3DM / GLB) and cache it locally.

        Returns the local path on success, *None* on failure.
        """
        local_name = Path(content_uri).name
        local_path = self.tiles_cache_dir / local_name
        if local_path.exists():
            return local_path

        url = f"{TILES_API_BASE}/{content_uri}?key={self.api_key}"
        resp = self.http_client.get(url)
        resp.raise_for_status()
        raw = resp.content

        # Write raw payload
        local_path.write_bytes(raw)

        # If B3DM, also extract and save the embedded GLB for convenience
        if local_path.suffix.lower() == ".b3dm":
            glb_data = _extract_glb_from_b3dm(raw)
            if glb_data is not None:
                glb_path = local_path.with_suffix(".glb")
                glb_path.write_bytes(glb_data)

        return local_path

    def _write_source_tiles(self, tiles: list[TileMetadata]) -> None:
        manifest = {
            "schema_version": "google3d.source_tiles.v1",
            "aoi_id": self.aoi_name,
            "provider": "google",
            "source": "photorealistic_3d_tiles",
            "status": "ingested",
            "tile_count": len(tiles),
            "tiles": [
                {
                    "tile_id": t.tile_id,
                    "content_uri": t.content_uri,
                    "bounding_region_deg": list(t.bounding_region_deg),
                    "geometric_error": t.geometric_error,
                }
                for t in tiles
            ],
        }
        manifest_path = self.tiles_cache_dir.parent / "source_tiles.json"
        with manifest_path.open("w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)


def _extract_glb_from_b3dm(data: bytes) -> bytes | None:
    """Extract the embedded GLB payload from a B3DM binary.

    B3DM header (28 bytes)::

        magic (4 bytes, "b3dm")
        version (4 bytes, uint32)
        byteLength (4 bytes, uint32)
        featureTableJSONByteLength (4 bytes, uint32)
        featureTableBinaryByteLength (4 bytes, uint32)
        batchTableJSONByteLength (4 bytes, uint32)
        batchTableBinaryByteLength (4 bytes, uint32)

    All table data follow the header, then the GLB payload.
    """
    if len(data) < 28:
        return None
    magic = data[:4]
    if magic != b"b3dm":
        return None
    (_mag, _ver, _total_len, ft_json_len, ft_bin_len, bt_json_len, bt_bin_len) = struct.unpack_from(
        "<4sIIIIII", data, 0
    )
    header_size = 28
    table_size = ft_json_len + ft_bin_len + bt_json_len + bt_bin_len
    glb_offset = header_size + table_size
    # Verify GLB magic
    if glb_offset + 4 <= len(data) and data[glb_offset:glb_offset + 4] == b"glTF":
        return data[glb_offset:]
    return None
