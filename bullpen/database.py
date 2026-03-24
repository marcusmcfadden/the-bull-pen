import os
import json
import bcrypt
import psycopg2
from typing import List, Tuple


DB_PATH = os.environ.get("BULLPEN_DB")

def _conn(write: bool = False):
    return psycopg2.connect(DB_PATH)

def init_db() -> None:
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        
        # Cadets Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS cadets (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            ms_level INTEGER,
            school TEXT,
            squad TEXT,
            tier INTEGER,
            email TEXT,
            phone TEXT
        );
        """)

        # Authenticate Users

        cur.execute("""
    CREATE TABLE IF NOT EXISTS auth_users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        reset_required INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(id) REFERENCES cadets(id) ON DELETE CASCADE
    );
        """)

        # Historical Event Log (Timestamped)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_events (
            id SERIAL PRIMARY KEY,
            cadet_id INTEGER NOT NULL REFERENCES cadets(id) ON DELETE CASCADE,
            event_ts INTEGER NOT NULL,
            status TEXT NOT NULL,
            is_late INTEGER NOT NULL DEFAULT 0,
            source TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Current Attendance Snapshot (For UI Performance)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance_current (
                cadet_id INTEGER,
                day TEXT,
                status TEXT,
                is_late INTEGER,
                updated_ts INTEGER,
                PRIMARY KEY (cadet_id, day),
                FOREIGN KEY(cadet_id) REFERENCES cadets(id) ON DELETE CASCADE
            );
        """)

        # Export Tracking
        cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_exports (
            id SERIAL PRIMARY KEY,
            label TEXT,
            start_ts INTEGER,
            end_ts INTEGER,
            exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Log Service
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            actor_id INTEGER,
            actor_role INTEGER,

            action TEXT NOT NULL,
            status TEXT NOT NULL,

            target_type TEXT,
            target_id INTEGER,

            location TEXT,
            ip_address TEXT,

            metadata JSONB
        );
        """)

        conn.commit()
    finally:
        conn.close()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def update_user_password(user_id: int, new_password: str):
    conn = _conn(write=True)
    try:
        cur = conn.cursor()

        cur.execute("""
            UPDATE auth_users
            SET password_hash = %s
            WHERE id = %s
        """, (hash_password(new_password), user_id))

        conn.commit()
    finally:
        conn.close()

# Authentication Logic

def create_auth_user(cadet_id: int, username: str, password: str):
    conn = _conn(write=True)
    try:
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO auth_users (id, username, password_hash)
            VALUES (%s, %s, %s)
        """, (cadet_id, username, hash_password(password)))

        conn.commit()
    finally:
        conn.close()

def login_user(username: str, password: str):
    conn = _conn()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT id, password_hash
            FROM auth_users
            WHERE username = %s
        """, (username,))

        row = cur.fetchone()
        if not row:
            return None

        cadet_id, stored_hash = row

        if verify_password(password, stored_hash):
            return cadet_id

        return None
    finally:
        conn.close()

# Cadet Management

def register_cadet(name: str, ms_level: int, school: str, squad: str, tier: int, email: str, phone: str) -> int:
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cadets (name, ms_level, school, squad, tier, email, phone)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (name, ms_level, school, squad, tier, email, phone))

        cadet_id = cur.fetchone()[0]
        conn.commit()
        return cadet_id
    finally:
        conn.close()

def update_cadet(cadet_id: int, name: str, ms_level: int, school: str, squad: str, tier: int, email: str, phone: str):
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE cadets SET name=%s, ms_level=%s, school=%s, squad=%s, tier=%s, email=%s, phone=%s
            WHERE id=%s
        """, (name, ms_level, school, squad, tier, cadet_id))
        conn.commit()
    finally:
        conn.close()

def delete_cadet(cadet_id: int):
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM cadets WHERE id = %s", (cadet_id,))
        conn.commit()
    finally:
        conn.close()

def get_filtered_cadets(query: str = "", schools=None, squads=None, ms_levels=None, order_direction="ASC"):
    conn = _conn()
    try:
        cur = conn.cursor()
        clauses, params = [], []
        if query:
            clauses.append("LOWER(name) LIKE %s")
            params.append(f"%{query.lower()}%")
        if schools:
            clauses.append(f"school IN ({','.join('%s'*len(schools))})")
            params.extend(schools)
        if squads:
            clauses.append(f"squad IN ({','.join('%s'*len(squads))})")
            params.extend(squads)
        if ms_levels:
            clauses.append(f"ms_level IN ({','.join('%s'*len(ms_levels))})")
            params.extend(ms_levels)
        
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT id, name, ms_level, school, squad, tier FROM cadets {where_sql} ORDER BY name {order_direction}"
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()

# Attendance Log

def upsert_attendance_current(cadet_id, day, status, is_late):
    import time

    conn = _conn(write=True)
    cur = conn.cursor()

    ts = int(time.time())

    cur.execute("""
        INSERT INTO attendance_current (cadet_id, day, status, is_late, updated_ts)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (cadet_id, day)
        DO UPDATE SET
            status = EXCLUDED.status,
            is_late = EXCLUDED.is_late,
            updated_ts = EXCLUDED.updated_ts
    """, (cadet_id, day, status, is_late, ts))

    conn.commit()
    conn.close()

def append_attendance_events(events_list: List[Tuple]):
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        for ev in events_list:
            cid, ts, stat, late, src, meta = ev
            meta_json = json.dumps(meta)

            day = meta.get("label")  # <-- IMPORTANT

            # 1. Log historical event
            cur.execute("""
                INSERT INTO attendance_events (cadet_id, event_ts, status, is_late, source, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (cid, ts, stat, late, src, meta_json))

            # 2. Update snapshot (correct syntax)
            cur.execute("""
                INSERT INTO attendance_current (cadet_id, day, status, is_late, updated_ts)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(cadet_id, day) DO UPDATE SET
                    status=excluded.status,
                    is_late=excluded.is_late,
                    updated_ts=excluded.updated_ts
            """, (cid, day, stat, late, ts))

        conn.commit()
    finally:
        conn.close()

def create_attendance_export(label: str, start_ts: int, end_ts: int, backup: bool = True) -> int:
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO attendance_exports (label, start_ts, end_ts)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (label, start_ts, end_ts))

        export_id = cur.fetchone()[0]
        conn.commit()
        return export_id
    finally:
        conn.close()

def clear_attendance_for_new_week(clear_events_in_range=None, reset_current=True, backup=True):
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        if clear_events_in_range:
            cur.execute("DELETE FROM attendance_events WHERE event_ts BETWEEN %s AND %s", clear_events_in_range)
        if reset_current:
            cur.execute("UPDATE attendance_current SET status = NULL, is_late = 0, updated_ts = NULL")
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Creating database...")
    init_db()
    print("Done.")