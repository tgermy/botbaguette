import os
import re
import sqlite3
import time
from typing import Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "botbaguette.db")

DEFAULT_PROFILE: Dict[str, Any] = {
    "pseudo": "",
    "marteaux": 0,
    "competences": 0,
    "cles_monture": 0,
    "potions": 0,
    "fioles_vertes": 0,
    "oeufs": 0,
    "fusion_montures": 0,
    "fusion_pets": 0,
    # Champs secrets (non affichés sur /profil, utilisés pour affiner les points potentiels)
    "skill_summon_cost": 40.0,
    "mount_summon_cost": 50.0,
    "egg_summon_cost": 100.0,
    "forge_tier_j1": 5,
    "forge_tier_j3": 4,
    "egg_rarity_json": "{}",
    "tech_tree_json": "{}",
    "updated_at": 0,
}

ALLOWED_COLUMNS = set(DEFAULT_PROFILE.keys())

_SUFFIXES = {
    "k": 1_000,
    "m": 1_000_000,
    "b": 1_000_000_000,
    "t": 1_000_000_000_000,
}

_AMOUNT_RE = re.compile(r"^\s*([0-9]+(?:[.,][0-9]+)?)\s*([kmbt])?\s*$", re.IGNORECASE)


def parse_amount(raw: str) -> int:
    """Parse Forge Master amounts like '181032', '181 032', '14.4k', '75,1k', '2.08m'."""
    cleaned = raw.replace(" ", "").replace("\u202f", "").replace("\u00a0", "")
    match = _AMOUNT_RE.match(cleaned)
    if not match:
        raise ValueError("Format invalide (ex: `181032`, `14.4k`, `2.08m`).")
    value = float(match.group(1).replace(",", "."))
    suffix = (match.group(2) or "").lower()
    result = int(round(value * _SUFFIXES.get(suffix, 1)))
    if result < 0:
        raise ValueError("La valeur doit être positive.")
    return result


def format_amount(value: int) -> str:
    """Format integer cleanly with spaces, or compact m/b for huge values."""
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}b".rstrip("0").rstrip(".")
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}m".rstrip("0").rstrip(".")
    return f"{value:,}".replace(",", " ")


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                pseudo TEXT DEFAULT '',
                marteaux INTEGER DEFAULT 0,
                competences INTEGER DEFAULT 0,
                cles_monture INTEGER DEFAULT 0,
                potions INTEGER DEFAULT 0,
                fioles_vertes INTEGER DEFAULT 0,
                oeufs INTEGER DEFAULT 0,
                fusion_montures INTEGER DEFAULT 0,
                fusion_pets INTEGER DEFAULT 0,
                skill_summon_cost REAL DEFAULT 40.0,
                mount_summon_cost REAL DEFAULT 50.0,
                egg_summon_cost REAL DEFAULT 100.0,
                forge_tier_j1 INTEGER DEFAULT 5,
                forge_tier_j3 INTEGER DEFAULT 4,
                egg_rarity_json TEXT DEFAULT '{}',
                tech_tree_json TEXT DEFAULT '{}',
                updated_at INTEGER DEFAULT 0
            )
            """
        )
        # Safe migrations for existing databases
        migrations = [
            ("fioles_vertes", "INTEGER DEFAULT 0"),
            ("fusion_montures", "INTEGER DEFAULT 0"),
            ("fusion_pets", "INTEGER DEFAULT 0"),
            ("skill_summon_cost", "REAL DEFAULT 40.0"),
            ("mount_summon_cost", "REAL DEFAULT 50.0"),
            ("egg_summon_cost", "REAL DEFAULT 100.0"),
            ("forge_tier_j1", "INTEGER DEFAULT 5"),
            ("forge_tier_j3", "INTEGER DEFAULT 4"),
            ("egg_rarity_json", "TEXT DEFAULT '{}'"),
            ("tech_tree_json", "TEXT DEFAULT '{}'"),
        ]
        for col, col_type in migrations:
            try:
                conn.execute(f"ALTER TABLE profiles ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass
        conn.commit()


def get_or_create_profile(user_id: int, default_pseudo: str = "", db_path: Optional[str] = None) -> Dict[str, Any]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            now = int(time.time())
            conn.execute(
                "INSERT INTO profiles (user_id, pseudo, updated_at) VALUES (?, ?, ?)",
                (user_id, default_pseudo, now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        profile = dict(row)
        if not profile.get("pseudo") and default_pseudo:
            profile["pseudo"] = default_pseudo
        return profile


def update_profile(user_id: int, updates: Dict[str, Any], db_path: Optional[str] = None) -> Dict[str, Any]:
    filtered = {k: v for k, v in updates.items() if k in ALLOWED_COLUMNS}
    if not filtered:
        return get_or_create_profile(user_id, db_path=db_path)

    filtered["updated_at"] = int(time.time())
    set_clause = ", ".join(f"{col} = ?" for col in filtered.keys())
    values = list(filtered.values()) + [user_id]

    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO profiles (user_id, updated_at) VALUES (?, ?)",
            (user_id, filtered["updated_at"]),
        )
        conn.execute(f"UPDATE profiles SET {set_clause} WHERE user_id = ?", values)
        conn.commit()
        row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row)
