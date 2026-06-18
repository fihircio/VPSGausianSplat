from fastapi import APIRouter, Query

from backend.utils.metrics import (
    get_all_scene_stats,
    get_daily_query_counts,
    get_total_queries,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def analytics_overview():
    return {
        "total_queries": get_total_queries(),
        "scenes": get_all_scene_stats(),
    }


@router.get("/daily")
def analytics_daily(days: int = Query(14, ge=1, le=90)):
    return {"daily": get_daily_query_counts(days)}
