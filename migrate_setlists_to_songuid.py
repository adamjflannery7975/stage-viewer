#!/usr/bin/env python3
"""
One-time migration: setlists.json -> song_uid canonical

- Reads ./library/setlists.json
- Builds uid -> song_uid map from ./songs/**/*.cho tag blocks
- Rewrites each set item to include song_uid, and de-dupes per set by song_uid
- Writes ./library/setlists.migrated.json (does not overwrite originals)

Run:
  python3 migrate_setlists_to_songuid.py
"""

from __future__ import annotations
import json, re, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SONGS_DIR = ROOT / "songs"
LIB_DIR   = ROOT / "library"
IN_FILE   = LIB_DIR / "setlists.json"
OUT_FILE  = LIB_DIR / "setlists.migrated.json"

TAG_LINE_RE = re.compile(r'^\s*\{([^}:]+)\s*:\s*(.*?)\}\s*$', re.I)

def parse_tag_block(text: str):
    tags = {}
    for line in text.splitlines():
        s = line.strip()
        if s == "":
            continue
        m = TAG_LINE_RE.match(s)
        if not m:
            break
        tags[m.group(1).strip().lower()] = m.group(2).strip()
    return tags

def build_uid_map():
    m = {}
    for p in SONGS_DIR.rglob("*.cho"):
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        tags = parse_tag_block(txt)
        uid = (tags.get("uid") or "").strip()
        song_uid = (tags.get("song_uid") or "").strip()
        if uid and song_uid:
            m[uid] = song_uid
    return m

def main():
    if not IN_FILE.exists():
        print(f"ERROR: missing {IN_FILE}")
        return

    uid_map = build_uid_map()
    data = json.loads(IN_FILE.read_text(encoding="utf-8"))

    def item_key(it):
        return (it.get("song_uid") or it.get("uid") or "").strip()

    # Support both possible shapes:
    #  - {"collections":[...]} or direct list of collections
    collections = data.get("collections") if isinstance(data, dict) else data
    if not isinstance(collections, list):
        print("ERROR: unexpected setlists.json structure (expected list or {collections:[]})")
        return

    changed = 0
    for col in collections:
        sets = col.get("sets") if isinstance(col, dict) else None
        if not isinstance(sets, list):
            continue
        for st in sets:
            songs = st.get("songs")
            if not isinstance(songs, list):
                continue
            new_songs = []
            seen = set()
            for it in songs:
                if not isinstance(it, dict):
                    continue
                uid = (it.get("uid") or "").strip()
                song_uid = (it.get("song_uid") or "").strip()
                if not song_uid and uid and uid in uid_map:
                    song_uid = uid_map[uid]
                    it["song_uid"] = song_uid
                    changed += 1
                k = (song_uid or uid).strip()
                if not k:
                    continue
                if k in seen:
                    changed += 1
                    continue
                seen.add(k)
                new_songs.append(it)
            st["songs"] = new_songs

    out = {"collections": collections} if isinstance(data, dict) else collections
    OUT_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Done. Wrote {OUT_FILE}. Items changed/removed: {changed}")

if __name__ == "__main__":
    main()
