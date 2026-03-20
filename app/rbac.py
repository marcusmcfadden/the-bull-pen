from typing import Optional, Dict, Any
from database import _conn
import bcrypt

# Tiers

tier_superadmin = 0
tier_admin = 1
tier_leader = 2
tier_cadet = 3

tier_names = {
    tier_admin: "SUPERADMIN",
    tier_admin: "ADMIN",
    tier_leader: "SQUAD LEADER",
    tier_cadet: "CADET",
}

tier_permissions = {
    tier_admin: {"view", "edit", "delete", "export", "attendance", "modulate"},
    tier_leader: {"view", "edit", "attendance", "modulate_limited"},
    tier_cadet: {"view", "attendance"},
}


# Helpers

def tier_name(tier: int) -> str:
    return tier_names.get(tier, "UNKNOWN")


def has_permission(tier: int, permission: str) -> bool:
    return permission in tier_permissions.get(tier, set())


def is_self(actor: Dict, target: Dict) -> bool:
    return actor["id"] == target["id"]


def has_authority(actor: Dict, target: Dict) -> bool:
    return actor["tier"] < target["tier"]


def same_squad(actor: Dict, target: Dict) -> bool:
    return actor.get("squad") == target.get("squad")


# Object-Level Permissions

def can_view(actor: Dict, target: Dict) -> bool:
    return True


def can_edit(actor: Dict, target: Dict) -> bool:

    actor_tier = actor["tier"]
    target_tier = target["tier"]

    if actor_tier == 0:
        return True

    if actor_tier == 1:
        return target_tier > 1

    return actor["id"] == target["id"]


def can_delete(actor: Dict, target: Dict) -> bool:
    return actor["tier"] == tier_admin


# Authentication

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                a.id,
                a.password_hash,
                c.name,
                c.tier,
                c.squad,
                c.ms_level,
                c.school
            FROM auth_users a
            JOIN cadets c ON a.id = c.id
            WHERE a.username = ?
        """, (username,))

        row = cur.fetchone()
        if not row:
            return None

        user_id, stored_hash, name, tier, squad, ms_level, school = row

        if not bcrypt.checkpw(password.encode(), stored_hash.encode()):
            return None

        return {
            "id": user_id,
            "name": name,
            "tier": tier,
            "tier_name": tier_name(tier),
            "squad": squad,
            "ms_level": ms_level,
            "school": school,
        }

    finally:
        conn.close()


# Tier Modulation

def can_modulate_tier(actor: Dict, target: Dict, new_tier: int) -> bool:
    actor_tier = actor["tier"]

    actor_tier = actor["tier"]
    target_tier = target["tier"]

    if actor_tier == tier_superadmin:
        return True

    if actor_tier == tier_admin:

        # must outrank target
        if actor_tier >= target_tier:
            return False

        # can only assign leader or cadet
        if new_tier in (tier_leader, tier_cadet):
            return True

        return False

    return False


def update_user_tier(actor: Dict, target_user_id: int, new_tier: int) -> bool:
    conn = _conn(write=True)
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT id, tier, squad
            FROM cadets
            WHERE id = ?
        """, (target_user_id,))
        row = cur.fetchone()

        if not row:
            return False

        target = {
            "id": row[0],
            "tier": row[1],
            "squad": row[2],
        }

        if not can_modulate_tier(actor, target, new_tier):
            return False

        cur.execute("""
            UPDATE cadets
            SET tier = ?
            WHERE id = ?
        """, (new_tier, target_user_id))

        conn.commit()
        return True

    finally:
        conn.close()


# Fetch Helpers

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, tier, squad, ms_level, school
            FROM cadets
            WHERE id = ?
        """, (user_id,))
        row = cur.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "name": row[1],
            "tier": row[2],
            "tier_name": tier_name(row[2]),
            "squad": row[3],
            "ms_level": row[4],
            "school": row[5],
        }

    finally:
        conn.close()