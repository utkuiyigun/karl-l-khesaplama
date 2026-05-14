"""
Celery task'ları.

Mimari:
- Beat → dispatch_sync_for_all_active_connections (5 dk'da bir)
   → her aktif bağlantı için sync_orders_for_connection.delay(connection_id) fan-out
- sync_orders_for_connection ZHATA otomatik retry (exponential backoff)
"""
import asyncio
from typing import Any

import structlog

from app.services.order_sync import find_active_connection_ids, sync_connection_orders
from app.workers.celery_app import celery_app

log = structlog.get_logger(__name__)


@celery_app.task(name="app.workers.tasks.dispatch_sync_for_all_active_connections")
def dispatch_sync_for_all_active_connections() -> dict[str, Any]:
    """Beat tarafından periyodik tetiklenir; aktif bağlantı başına alt-task üretir."""
    connection_ids = asyncio.run(find_active_connection_ids())
    for cid in connection_ids:
        sync_orders_for_connection.delay(cid)
    log.info("dispatched_sync_jobs", count=len(connection_ids))
    return {"dispatched": len(connection_ids), "connection_ids": connection_ids}


@celery_app.task(
    name="app.workers.tasks.sync_orders_for_connection",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
)
def sync_orders_for_connection(self, connection_id: int) -> dict[str, Any]:  # noqa: ARG001
    """Tek bir bağlantı için sync; hata olursa exponential backoff ile retry."""
    return asyncio.run(sync_connection_orders(connection_id))
