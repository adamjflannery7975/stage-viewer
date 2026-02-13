#!/usr/bin/env python3
"""
Migrate ChordPro Studio setlists.json from sheet uids -> canonical song_uid.

Reads:
  - ./songs/*.cho (extract {uid:} and {song_uid:})
  - ./library/setlists.json

Writes:
  - ./library/setlists.migrated.json (does NOT overwrite original)
  - ./library/migrate_setlists.log.json

Rules:
  - If a song entry matches a sheet uid found in .cho, replace with its song_uid.
  - If missing song_uid, falls back to the uid (no change).
  - De-dupes songs within each set after migration (preserves order of first occurrences).
"""

from __future__ import annotations
import json, os, re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

TAG_RE = re.compile(r"^\s*\{([a-zA-Z0-9_\-]+)\s*:\s*(.*?)\}\s*$")

def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def parse_tags(text: str) -> Dict[str,str]:
    out: Dict[str,str] = {}
    for line in text.splitlines():
        m = TAG_RE.match(line)
        if not m: 
            continue
        k = m.group(1).strip().lower()
        v = m.group(2).strip()
        if k not in out:
            out[k] = v
    return out

def build_uid_map(repo_root: Path) -> Dict[str,str]:
    songs_dir = repo_root / "songs"
    uid_to_song: Dict[str,str] = {}
    for f in sorted(songs_dir.rglob("*.cho")):
        tags = parse_tags(read_text(f))
        uid = (tags.get("uid") or "").strip()
        song_uid = (tags.get("song_uid") or tags.get("songuid") or "").strip()
        if uid:
            uid_to_song[uid] = song_uid or uid
    return uid_to_song

def load_setlists(p: Path) -> dict:
    if not p.exists():
        return {"version": 1, "updated": now_iso(), "collections": []}
    data = json.loads(read_text(p))
    # supports old/new, same as consolidate_library.py
    if isinstance(data, dict) and "collections" in data:
        return data
    if isinstance(data, dict) and "setlists" in data:
        migrated = {"version": data.get("version", 1), "updated": now_iso(), "collections": []}
        for sl in data.get("setlists", []):
            migrated["collections"].append({
                "id": sl.get("id") or sl.get("name") or "",
                "type": "gig",
                "name": sl.get("name") or sl.get("id") or "Unnamed",
                "notes": sl.get("notes", ""),
                "sets": sl.get("sets", [])
            })
        return migrated
    raise RuntimeError("setlists.json must contain 'collections' or 'setlists'")

def dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in items:
        if x in seen: 
            continue
        seen.add(x)
        out.append(x)
    return out

def main():
    repo_root = Path(".").resolve()
    uid_map = build_uid_map(repo_root)

    lib_dir = repo_root / "library"
    src = lib_dir / "setlists.json"
    out = lib_dir / "setlists.migrated.json"
    logp = lib_dir / "migrate_setlists.log.json"
    lib_dir.mkdir(parents=True, exist_ok=True)

    data = load_setlists(src)
    changed = 0
    missing = 0

    for col in data.get("collections", []):
        for st in col.get("sets", []):
            songs = st.get("songs", [])
            if not isinstance(songs, list):
                continue
            new_songs = []
            for uid in songs:
                key = str(uid)
                canon = uid_map.get(key)
                if canon is None:
                    # unknown uid - keep as-is and log
                    missing += 1
                    canon = key
                if canon != key:
                    changed += 1
                new_songs.append(canon)
            st["songs"] = dedupe_preserve_order(new_songs)

    data["updated"] = now_iso()
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logp.write_text(json.dumps({"written": str(out), "changed": changed, "unknown_refs": missing, "ts": now_iso()}, indent=2), encoding="utf-8")

    print("✅ Wrote", out)
    print(" - Converted refs:", changed)
    print(" - Unknown refs kept:", missing)

if __name__ == "__main__":
    main()
