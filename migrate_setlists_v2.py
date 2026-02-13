#!/usr/bin/env python3
"""
migrate_setlists_v2.py
----------------------
Reads:  library/setlists.json   (legacy)
Writes: library/setlists.v2.json (canonical song_uid)

Supports legacy structure where set.songs is a list of strings like:
  ["uid-...", "uid-..."]

It converts any uid -> song_uid using tag blocks in songs/**/*.cho
It also de-dupes within each set by song_uid while preserving order.
"""

import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SONGS_DIR = ROOT / "songs"
LIB_DIR = ROOT / "library"
IN_FILE = LIB_DIR / "setlists.json"
OUT_FILE = LIB_DIR / "setlists.v2.json"

TAG_LINE_RE = re.compile(r'^\s*\{([^}:]+)\s*:\s*(.*?)\}\s*$', re.I)

def parse_tag_block(text: str):
    tags = {}
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = TAG_LINE_RE.match(s)
        if not m:
            break
        tags[m.group(1).strip().lower()] = m.group(2).strip()
    return tags

def build_uid_to_songuid():
    m = {}
    for p in SONGS_DIR.rglob("*.cho"):
        txt = p.read_text(encoding="utf-8", errors="replace")
        tags = parse_tag_block(txt)
        uid = (tags.get("uid") or "").strip()
        song_uid = (tags.get("song_uid") or "").strip()
        if uid and song_uid:
            m[uid] = song_uid
    return m

def main():
    if not IN_FILE.exists():
        raise SystemExit(f"Missing {IN_FILE}")

    uid_map = build_uid_to_songuid()
    data = json.loads(IN_FILE.read_text(encoding="utf-8"))

    collections = data.get("collections") if isinstance(data, dict) else None
    if not isinstance(collections, list):
        raise SystemExit("Unexpected setlists.json format (expected {collections:[...]})")

    changed = 0
    removed_dupes = 0
    unresolved = 0

    for col in collections:
        for st in col.get("sets", []):
            songs = st.get("songs", [])
            if not isinstance(songs, list):
                continue

            new_list = []
            seen = set()

            for item in songs:
                if not isinstance(item, str):
                    continue
                key = item.strip()

                # Convert uid -> song_uid if needed
                if key.startswith("uid-"):
                    song_uid = uid_map.get(key)
                    if song_uid:
                        key = song_uid
                        changed += 1
                    else:
                        unresolved += 1  # uid not found in map; keep as-is for now

                # De-dupe within set
                if key in seen:
                    removed_dupes += 1
                    continue
                seen.add(key)
                new_list.append(key)

            st["songs"] = new_list

    out = {
        "version": 2,
        "contract": "song_uid_v2",
        "collections": collections
    }
    OUT_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Done. Wrote {OUT_FILE}")
    print(f"converted:{changed} removed_dupes:{removed_dupes} unresolved_uids:{unresolved}")

if __name__ == "__main__":
    main()