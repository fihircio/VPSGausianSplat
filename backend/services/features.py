import faiss
import numpy as np
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.feature_set import FeatureSet
from backend.models.scene import Scene
from backend.services.feature_mapper import FeatureMapper
from backend.utils.config import get_settings
from backend.utils.storage import get_storage


class FeatureService:
    @staticmethod
    def build_scene_feature_index(scene: Scene, db: Session) -> FeatureSet:
        storage = get_storage()
        settings = get_settings()
        
        # Mapping returns SceneFeatureMapping and remote_db_path string
        mapping, _ = FeatureMapper.build_scene_mapping(scene=scene, db=db)

        feature_dir_remote = f"features/{scene.id}"
        local_feature_dir = storage.ensure_local_copy(feature_dir_remote)
        local_feature_dir.mkdir(parents=True, exist_ok=True)
        
        index_path_local = local_feature_dir / "features.faiss"
        metadata_path_local = local_feature_dir / "scene_features.npz"

        descriptors_fp32 = mapping.descriptors.astype(np.float32)
        index = faiss.IndexFlatL2(descriptors_fp32.shape[1])
        index.add(descriptors_fp32)
        faiss.write_index(index, str(index_path_local))

        np.savez_compressed(
            str(metadata_path_local),
            points3d=mapping.points3d_xyz.astype(np.float32),
            point3d_ids=mapping.point3d_ids.astype(np.int64),
            frame_ids=mapping.frame_ids.astype(np.int64),
        )

        # Sync back to remote
        if settings.storage_backend.upper() != "LOCAL":
            storage.sync_dir_to_remote(local_feature_dir, feature_dir_remote)

        feature_set = db.scalar(
            select(FeatureSet).where(FeatureSet.scene_id == scene.id).order_by(desc(FeatureSet.id))
        )
        if feature_set is None:
            feature_set = FeatureSet(scene_id=scene.id, index_path="", metadata_path="", num_descriptors=0)

        feature_set.index_path = f"{feature_dir_remote}/features.faiss"
        feature_set.metadata_path = f"{feature_dir_remote}/scene_features.npz"
        feature_set.num_descriptors = int(mapping.descriptors.shape[0])
        feature_set.feature_mode = settings.feature_mode
        db.add(feature_set)

        scene.faiss_index_path = feature_set.index_path
        scene.feature_meta_path = feature_set.metadata_path
        db.add(scene)
        db.commit()
        db.refresh(feature_set)
        return feature_set
