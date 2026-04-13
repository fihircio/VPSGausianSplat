import faiss
import numpy as np
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.models.feature_set import FeatureSet
from backend.models.scene import Scene
from backend.services.feature_mapper import FeatureMapper


class FeatureService:
    @staticmethod
    def build_scene_feature_index(scene: Scene, db: Session) -> FeatureSet:
        mapping, scene_db_path = FeatureMapper.build_scene_mapping(scene=scene, db=db)

        feature_dir = scene_db_path.parent
        index_path = feature_dir / "orb.faiss"
        metadata_path = feature_dir / "scene_features.npz"

        descriptors_fp32 = mapping.descriptors_uint8.astype(np.float32)
        index = faiss.IndexFlatL2(descriptors_fp32.shape[1])
        index.add(descriptors_fp32)
        faiss.write_index(index, str(index_path))

        np.savez_compressed(
            str(metadata_path),
            points3d=mapping.points3d_xyz.astype(np.float32),
            point3d_ids=mapping.point3d_ids.astype(np.int64),
            frame_ids=mapping.frame_ids.astype(np.int64),
        )

        feature_set = db.scalar(
            select(FeatureSet).where(FeatureSet.scene_id == scene.id).order_by(desc(FeatureSet.id))
        )
        if feature_set is None:
            feature_set = FeatureSet(scene_id=scene.id, index_path="", metadata_path="", num_descriptors=0)

        feature_set.index_path = str(index_path.resolve())
        feature_set.metadata_path = str(metadata_path.resolve())
        feature_set.num_descriptors = int(mapping.descriptors_uint8.shape[0])
        db.add(feature_set)

        scene.faiss_index_path = feature_set.index_path
        scene.feature_meta_path = feature_set.metadata_path
        db.add(scene)
        db.commit()
        db.refresh(feature_set)
        return feature_set

    @staticmethod
    def extract_orb(image_path):
        return FeatureMapper.extract_orb_features(image_path)
