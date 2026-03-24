from datetime import datetime, timezone
from database import _conn


def log_event(
    actor_id: int,
    action: str,
    status: str,
    actor_role: int = None,
    target_id: int = None,
    target_type: str = None,
    location: str = None,
    ip_address: str = None,
    metadata: dict = None
):
    conn = _conn(write=True)
    try:
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO audit_logs (
                timestamp,
                actor_id,
                actor_role,
                action,
                status,
                target_type,
                target_id,
                location,
                ip_address,
                metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            datetime.now(timezone.utc),
            actor_id,
            actor_role,
            action,
            status,
            target_type,
            target_id,
            location,
            ip_address,
            metadata
        ))

        conn.commit()

    finally:
        conn.close()

def get_logs(limit=50):
    conn = _conn()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT timestamp, actor_id, actor_role, action, status, target_id
            FROM audit_logs
            ORDER BY timestamp ASC
            LIMIT %s
        """, (limit,))

        rows = cur.fetchall()

        logs = []
        for r in rows:
            logs.append({
                "timestamp": r[0],
                "actor_id": r[1],
                "actor_role": r[2],
                "action": r[3],
                "status": r[4],
                "target_id": r[5],
            })

        return logs

    finally:
        conn.close()