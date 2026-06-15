"""AOI and permission metadata models for the Google 3D scaffold."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.services.google3d.transforms import WGS84Point, wgs84_to_ecef


@dataclass(frozen=True)
class DataPermission:
    provider: str = "google"
    source: str = "photorealistic_3d_tiles"
    allowed_uses: tuple[str, ...] = ("internal_research_only",)
    allowed_storage: tuple[str, ...] = ()
    derived_model_commercialization: bool | None = None
    retention_days: int | None = None
    document_uri: str | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "DataPermission":
        if value is None:
            return cls()
        return cls(
            provider=str(value.get("provider", "google")),
            source=str(value.get("source", "photorealistic_3d_tiles")),
            allowed_uses=tuple(value.get("allowed_uses", ("internal_research_only",))),
            allowed_storage=tuple(value.get("allowed_storage", ())),
            derived_model_commercialization=value.get("derived_model_commercialization"),
            retention_days=value.get("retention_days"),
            document_uri=value.get("document_uri"),
        )

    @property
    def is_research_only(self) -> bool:
        return "internal_research_only" in self.allowed_uses

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "source": self.source,
            "allowed_uses": list(self.allowed_uses),
            "allowed_storage": list(self.allowed_storage),
            "derived_model_commercialization": self.derived_model_commercialization,
            "retention_days": self.retention_days,
            "document_uri": self.document_uri,
        }


@dataclass(frozen=True)
class AOI:
    aoi_id: str
    name: str
    origin_wgs84: WGS84Point
    polygon_wgs84: tuple[WGS84Point, ...]
    market: str | None = None
    priority: int = 0
    vertical_datum: str = "unknown"
    local_frame: str = "ENU"
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "AOI":
        polygon = tuple(WGS84Point.from_mapping(point) for point in value["polygon_wgs84"])
        if len(polygon) < 3:
            raise ValueError("polygon_wgs84 must contain at least three points")
        local_frame = str(value.get("local_frame", "ENU"))
        if local_frame != "ENU":
            raise ValueError(f"unsupported local_frame {local_frame!r}; expected 'ENU'")
        return cls(
            aoi_id=str(value["aoi_id"]),
            name=str(value.get("name", value["aoi_id"])),
            origin_wgs84=WGS84Point.from_mapping(value["origin_wgs84"]),
            polygon_wgs84=polygon,
            market=value.get("market"),
            priority=int(value.get("priority", 0)),
            vertical_datum=str(value.get("vertical_datum", "unknown")),
            local_frame=local_frame,
            tags=tuple(value.get("tags", ())),
            metadata=dict(value.get("metadata", {})),
        )

    @property
    def origin_ecef(self) -> list[float]:
        return wgs84_to_ecef(self.origin_wgs84).to_list()

    def to_dict(self) -> dict[str, Any]:
        return {
            "aoi_id": self.aoi_id,
            "name": self.name,
            "market": self.market,
            "priority": self.priority,
            "origin_wgs84": self.origin_wgs84.to_dict(),
            "origin_ecef": self.origin_ecef,
            "local_frame": self.local_frame,
            "vertical_datum": self.vertical_datum,
            "polygon_wgs84": [point.to_dict() for point in self.polygon_wgs84],
            "tags": list(self.tags),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class AOIRegistry:
    aois: tuple[AOI, ...]
    permission: DataPermission = field(default_factory=DataPermission)
    schema_version: str = "google3d.aoi_registry.v1"

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "AOIRegistry":
        return cls(
            aois=tuple(AOI.from_mapping(item) for item in value.get("aois", ())),
            permission=DataPermission.from_mapping(value.get("permission")),
            schema_version=str(value.get("schema_version", "google3d.aoi_registry.v1")),
        )

    @classmethod
    def load(cls, path: Path) -> "AOIRegistry":
        with path.open("r", encoding="utf-8") as fh:
            return cls.from_mapping(json.load(fh))

    def get(self, aoi_id: str) -> AOI:
        for aoi in self.aois:
            if aoi.aoi_id == aoi_id:
                return aoi
        raise KeyError(f"AOI {aoi_id!r} not found")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "permission": self.permission.to_dict(),
            "aois": [aoi.to_dict() for aoi in self.aois],
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, sort_keys=True)
            fh.write("\n")
