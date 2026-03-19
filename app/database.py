# database.py
import os
import sqlite3
import json
import time
import shutil
from typing import List, Tuple, Optional, Dict

DB_PATH = os.environ.get("BULLPEN_DB", "bullpen.db")

def _conn(write: bool = False) -> sqlite3.Connection:
    if write:
        return sqlite3.connect(DB_PATH, check_same_thread=False)
    return sqlite3.connect(DB_PATH)

def init_db() -> None:
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode = WAL;")
        
        # 1. Cadets Table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS cadets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ms_level INTEGER,
            school TEXT,
            squad TEXT,
            tier INTEGER,
            password_hash TEXT
        );
        """)

        # 2. Historical Event Log (Timestamped)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cadet_id INTEGER NOT NULL REFERENCES cadets(id) ON DELETE CASCADE,
            event_ts INTEGER NOT NULL,
            status TEXT NOT NULL,
            is_late INTEGER NOT NULL DEFAULT 0,
            source TEXT,
            metadata TEXT,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
        );
        """)

        # 3. Current Attendance Snapshot (For UI Performance)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_current (
            cadet_id INTEGER PRIMARY KEY REFERENCES cadets(id) ON DELETE CASCADE,
            status TEXT,
            is_late INTEGER,
            updated_ts INTEGER
        );
        """)

        # 4. Export Tracking
        cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_exports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT,
            start_ts INTEGER,
            end_ts INTEGER,
            exported_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
        );
        """)

        conn.commit()
    finally:
        conn.close()

# --- CADET MANAGEMENT ---

def register_cadet(name: str, ms_level: int, school: str, squad: str, tier: int, password_hash: str) -> int:
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cadets (name, ms_level, school, squad, tier, password_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, ms_level, school, squad, tier, password_hash))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def update_cadet(cadet_id: int, name: str, ms_level: int, school: str, squad: str, tier: int):
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE cadets SET name=?, ms_level=?, school=?, squad=?, tier=?
            WHERE id=?
        """, (name, ms_level, school, squad, tier, cadet_id))
        conn.commit()
    finally:
        conn.close()

def delete_cadet(cadet_id: int):
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM cadets WHERE id = ?", (cadet_id,))
        conn.commit()
    finally:
        conn.close()

def get_filtered_cadets(query: str = "", schools=None, squads=None, ms_levels=None, order_direction="ASC"):
    conn = _conn()
    try:
        cur = conn.cursor()
        clauses, params = [], []
        if query:
            clauses.append("LOWER(name) LIKE ?")
            params.append(f"%{query.lower()}%")
        if schools:
            clauses.append(f"school IN ({','.join('?'*len(schools))})")
            params.extend(schools)
        if squads:
            clauses.append(f"squad IN ({','.join('?'*len(squads))})")
            params.extend(squads)
        if ms_levels:
            clauses.append(f"ms_level IN ({','.join('?'*len(ms_levels))})")
            params.extend(ms_levels)
        
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT id, name, ms_level, school, squad, tier FROM cadets {where_sql} ORDER BY name {order_direction}"
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()

# --- ATTENDANCE LOGIC ---

def append_attendance_events(events_list: List[Tuple]):
    """
    Batch inserts events and updates the 'current' status snapshot.
    Expected format: (cadet_id, event_ts, status, is_late, source, metadata_dict)
    """
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        for ev in events_list:
            cid, ts, stat, late, src, meta = ev
            meta_json = json.dumps(meta)
            
            # 1. Log historical event
            cur.execute("""
                INSERT INTO attendance_events (cadet_id, event_ts, status, is_late, source, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (cid, ts, stat, late, src, meta_json))
            
            # 2. Update current snapshot
            cur.execute("""
                INSERT INTO attendance_current (cadet_id, status, is_late, updated_ts)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cadet_id) DO UPDATE SET
                    status=excluded.status, is_late=excluded.is_late, updated_ts=excluded.updated_ts
            """, (cid, stat, late, ts))
        conn.commit()
    finally:
        conn.close()

def create_attendance_export(label: str, start_ts: int, end_ts: int, backup: bool = True) -> int:
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO attendance_exports (label, start_ts, end_ts) VALUES (?, ?, ?)", (label, start_ts, end_ts))
        export_id = cur.lastrowid
        conn.commit()
        return export_id
    finally:
        conn.close()

def clear_attendance_for_new_week(clear_events_in_range=None, reset_current=True, backup=True):
    conn = _conn(write=True)
    try:
        cur = conn.cursor()
        if clear_events_in_range:
            cur.execute("DELETE FROM attendance_events WHERE event_ts BETWEEN ? AND ?", clear_events_in_range)
        if reset_current:
            cur.execute("UPDATE attendance_current SET status = NULL, is_late = 0, updated_ts = NULL")
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Creating database...")
    init_db()
    print("Done.")