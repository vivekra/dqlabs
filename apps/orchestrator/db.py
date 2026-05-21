"""
DigitalQ Labs — Synchronous Database Layer for Celery Workers
Uses psycopg2 directly for simple, reliable DB operations inside background tasks.
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras

from apps.orchestrator.config import settings

logger = logging.getLogger("digitalq-orchestrator.db")


def _parse_dsn() -> Dict[str, Any]:
    """Parse DATABASE_URL into psycopg2 connection kwargs."""
    parsed = urlparse(settings.DATABASE_URL)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "dbname": parsed.path.lstrip("/"),
        "user": parsed.username or "postgres",
        "password": parsed.password or "",
    }


@contextmanager
def get_connection():
    """Context manager yielding a psycopg2 connection with auto-commit on success."""
    conn = psycopg2.connect(**_parse_dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_workspace(workspace_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single workspace record by ID."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM workspaces WHERE id = %s",
                (workspace_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_workspace_with_template(workspace_id: str) -> Optional[Dict[str, Any]]:
    """Fetch workspace joined with its lab template manifest_spec and ai_runbook."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT w.*, 
                       t.manifest_spec AS template_manifest_spec,
                       t.title AS template_title,
                       t.ai_runbook AS template_ai_runbook
                FROM workspaces w
                LEFT JOIN lab_templates t ON w.template_id = t.id
                WHERE w.id = %s
                """,
                (workspace_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_tenant_quota(tenant_id: str) -> Optional[Dict[str, Any]]:
    """Fetch resource quota limits for a tenant."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM tenant_quotas WHERE tenant_id = %s",
                (tenant_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def get_workspaces_by_status(status: str) -> List[Dict[str, Any]]:
    """Fetch all workspaces matching a given status."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM workspaces WHERE status = %s",
                (status,),
            )
            return [dict(row) for row in cur.fetchall()]


def get_idle_workspaces(idle_minutes: int) -> List[Dict[str, Any]]:
    """Fetch running workspaces whose last_active_at exceeds the idle threshold."""
    threshold = datetime.now(timezone.utc) - timedelta(minutes=idle_minutes)
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM workspaces
                WHERE status = 'running'
                  AND last_active_at < %s
                """,
                (threshold,),
            )
            return [dict(row) for row in cur.fetchall()]


def update_workspace_status(
    workspace_id: str,
    status: str,
    pod_name: Optional[str] = None,
    namespace: Optional[str] = None,
    ingress_url: Optional[str] = None,
) -> None:
    """Update workspace status and optional runtime metadata."""
    fields = ["status = %s", "updated_at = NOW()"]
    params: list = [status]

    if pod_name is not None:
        fields.append("pod_name = %s")
        params.append(pod_name)
    if namespace is not None:
        fields.append("namespace = %s")
        params.append(namespace)
    if ingress_url is not None:
        fields.append("ingress_url = %s")
        params.append(ingress_url)

    params.append(workspace_id)
    sql = f"UPDATE workspaces SET {', '.join(fields)} WHERE id = %s"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)

    logger.info("Workspace %s status updated to '%s'", workspace_id, status)


def touch_workspace_activity(workspace_id: str) -> None:
    """Refresh last_active_at timestamp for a workspace."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE workspaces SET last_active_at = NOW() WHERE id = %s",
                (workspace_id,),
            )
