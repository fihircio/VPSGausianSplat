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
        scene.error_message = None
        db.add(scene)
        db.commit()

        ReconstructionService.extract_frames(scene, db, force_rebuild=force_rebuild)
        ReconstructionService.run_colmap(scene, db)
        SplattingService.run(scene, db)
        VPSService.build_feature_db(scene, db)

        scene.status = "READY"
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
