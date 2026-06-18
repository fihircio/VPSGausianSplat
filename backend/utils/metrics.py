import logging
import time
from datetime import date, datetime, timedelta
from functools import wraps

import redis

from backend.utils.config import get_settings

logger = logging.getLogger(__name__)


def get_redis_client():
    settings = get_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


def record_query(scene_id: str, success: bool, latency_ms: float):
    try:
        r = get_redis_client()
        today = date.today().isoformat()
        r.incr(f"vps:queries:total")
        r.incr(f"vps:queries:{scene_id}")
        r.incr(f"vps:daily:{today}")
        if success:
            r.incr(f"vps:success:{scene_id}")
        else:
            r.incr(f"vps:failure:{scene_id}")
        r.zadd(f"vps:latency:{scene_id}", {str(time.time()): latency_ms})
        r.expire(f"vps:latency:{scene_id}", 86400 * 30)
    except Exception as e:
        logger.warning(f"Metrics recording failed: {e}")


def get_scene_stats(scene_id: str) -> dict:
    try:
        r = get_redis_client()
        total = int(r.get(f"vps:queries:{scene_id}") or 0)
        success = int(r.get(f"vps:success:{scene_id}") or 0)
        failure = int(r.get(f"vps:failure:{scene_id}") or 0)
        latencies = r.zrange(f"vps:latency:{scene_id}", 0, -1, withscores=True)
        latency_values = sorted([v for _, v in latencies])
        stats = {
            "scene_id": scene_id,
            "total_queries": total,
            "success_count": success,
            "failure_count": failure,
            "success_rate": round(success / total, 4) if total > 0 else 0,
        }
        if latency_values:
            n = len(latency_values)
            stats["latency_ms"] = {
                "p50": round(latency_values[max(0, int(n * 0.50) - 1)], 2),
                "p95": round(latency_values[max(0, int(n * 0.95) - 1)], 2),
                "p99": round(latency_values[max(0, int(n * 0.99) - 1)], 2),
                "min": round(latency_values[0], 2),
                "max": round(latency_values[-1], 2),
                "samples": n,
            }
        else:
            stats["latency_ms"] = None
        return stats
    except Exception as e:
        logger.warning(f"Failed to fetch scene stats: {e}")
        return {"scene_id": scene_id, "error": str(e)}


def get_daily_query_counts(days: int = 14) -> list[dict]:
    try:
        r = get_redis_client()
        results = []
        for i in range(days):
            d = (date.today() - timedelta(days=days - 1 - i)).isoformat()
            count = int(r.get(f"vps:daily:{d}") or 0)
            results.append({"date": d, "queries": count})
        return results
    except Exception as e:
        logger.warning(f"Failed to fetch daily counts: {e}")
        return []


def get_all_scene_stats() -> list[dict]:
    try:
        r = get_redis_client()
        keys = r.keys("vps:queries:*")
        scene_ids = set()
        for k in keys:
            parts = k.split(":", 2)
            if len(parts) == 3 and parts[1] == "queries":
                scene_ids.add(parts[2])
        return [get_scene_stats(sid) for sid in sorted(scene_ids)]
    except Exception as e:
        logger.warning(f"Failed to list scene stats: {e}")
        return []


def get_total_queries() -> int:
    try:
        r = get_redis_client()
        return int(r.get("vps:queries:total") or 0)
    except Exception as e:
        logger.warning(f"Failed to get total queries: {e}")
        return 0
