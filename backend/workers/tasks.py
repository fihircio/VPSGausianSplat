from sqlalchemy.exc import SQLAlchemyError

from backend.models.scene import Scene
from backend.services.reconstruction import ReconstructionService
from backend.services.splatting import SplattingService
from backend.services.vps import VPSService
from backend.utils.db import SessionLocal
from backend.workers.celery_app import celery_app


@celery_app.task(name="scene.process")
def process_scene_task(scene_id: str, force_rebuild: bool = False) -> dict:
    db = SessionLocal()
    try:
        scene = db.get(Scene, scene_id)
        if not scene:
            return {"scene_id": scene_id, "status": "FAILED", "error": "Scene not found"}

        scene.status = "PROCESSING"
        scene.progress_percent = 5.0
        scene.current_task_label = "Initializing pipeline..."
        scene.error_message = None
        db.add(scene)
        db.commit()

        # Phase 1: Frame Extraction
        scene.progress_percent = 10.0
        scene.current_task_label = "Extracting video frames..."
        db.add(scene)
        db.commit()
        ReconstructionService.extract_frames(scene, db, force_rebuild=force_rebuild)

        # Phase 2: SfM (COLMAP)
        scene.progress_percent = 25.0
        scene.current_task_label = "Running Structure-from-Motion (COLMAP)..."
        db.add(scene)
        db.commit()
        ReconstructionService.run_colmap(scene, db)

        # Phase 3: Gaussian Splatting
        scene.progress_percent = 60.0
        scene.current_task_label = "Training Gaussian Splatting model..."
        db.add(scene)
        db.commit()
        SplattingService.run(scene, db)

        # Phase 4: VPS Indexing
        scene.progress_percent = 85.0
        scene.current_task_label = "Building VPS feature database..."
        db.add(scene)
        db.commit()
        VPSService.build_feature_db(scene, db)

        scene.status = "READY"
        scene.progress_percent = 100.0
        scene.current_task_label = "Processing complete"
        db.add(scene)
        db.commit()
        return {"scene_id": scene_id, "status": "READY"}
    except Exception as e:  # noqa: BLE001
        try:
            scene = db.get(Scene, scene_id)
            if scene:
                scene.status = "FAILED"
                scene.error_message = str(e)
                db.add(scene)
                db.commit()
        except SQLAlchemyError:
            db.rollback()
        return {"scene_id": scene_id, "status": "FAILED", "error": str(e)}
    finally:
        db.close()
