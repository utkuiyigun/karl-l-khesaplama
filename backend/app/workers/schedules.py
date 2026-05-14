"""
Celery Beat zamanlama tanımları.

ADR-002: Trendyol webhook vermez → her 5 dakikada bir polling.
SYNC_INTERVAL_MINUTES .env'den ayarlanır (default 5).
"""
from app.core.config import settings

beat_schedule: dict[str, dict] = {
    "sync-all-active-connections": {
        "task": "app.workers.tasks.dispatch_sync_for_all_active_connections",
        "schedule": settings.sync_interval_minutes * 60,  # saniyeye çevir
    },
}
