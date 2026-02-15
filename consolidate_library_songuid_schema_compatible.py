#!/usr/bin/env python3
"""
ChordPro Studio - consolidate_library.py (song_uid canonical, schema-compatible)

This script scans ./songs/**/*.cho and rebuilds:
  - ./library/songs.index.json
  - ./library/library.index.json

Key behavior:
- Treats {song_uid: ...} as the canonical song identifier (one logical song).
- Treats {uid: ...} as the sheet/version identifier (one file).
- Groups multiple sheets (different uid/version/persona) under the same song_uid.

Output schema is kept compatible with your existing apps:
library.index.json:
{
  "version": 2,
  "songs": [ { ... } ],
  "collections": [...]
}

songs.index.json:
{
  "version": 2,
  "songCount": <int>,
  "songs": [ { ... } ]
}

Per-song record (superset of current):
{
  "song_uid": "song-....",
  "uid": "uid-....",                 # representative sheet uid (preferred persona if available)
  "title": "...",
  "artist": "...",
  "personas": ["Adam","Pete"],
  "singer": "...",                  # representative
  "duration": "3:35",               # representative
  "tempo": 135,                     # representative
  "key": "A",
  "capo": "2",
  "files": { "Adam":"songs/...Adam.cho", "Pete":"songs/...Pete.cho" },
  "sheet_uids": { "Adam":"uid-...", "Pete":"uid-..." }   # NEW (helps migration/debug)
}

Notes:
- Representative values (uid/singer/duration/tempo/key/capo) are chosen by preferred persona:
    localStorage persona is runtime-only, so here we default to "Adam" if present, else first persona.
"""

from __future__ import annotations
import json, re, time, sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

ROOT = Path(__file__).resolve().parent
SONGS_DIR = ROOT / "songs"
LIB_DIR   = ROOT / "library"
OUT_SONGS = LIB_DIR / "songs.index.json"
OUT_LIB   = LIB_DIR / "library.index.json"

TAG_LINE_RE = re.compile(r'^\s*\{([^}:]+)\s*:\s*(.*?)\}\s*$', re.I)
CHO_EXTS = (".cho", ".chopro", ".pro")

PREFERRED_PERSONA = "Adam"

def log(msg: str):
  print(msg, flush=True)

def parse_tag_block(text: str) -> Dict[str, str]:
  tags: Dict[str, str] = {}
  for line in text.splitlines():
    s = line.strip()
    if s == "":
      continue
    m = TAG_LINE_RE.match(s)
    if not m:
      break
    tags[m.group(1).strip().lower()] = m.group(2).strip()
  return tags

def safe_int(v: str) -> int | None:
  try:
    return int(str(v).strip())
  except Exception:
    return None

def atomic_write_json(path: Path, data: Any):
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_suffix(path.suffix + ".tmp")
  tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  tmp.replace(path)

def relpath(p: Path) -> str:
  return str(p.relative_to(ROOT)).replace("\\", "/")

def main():
  if not SONGS_DIR.exists():
    log(f"ERROR: songs folder not found: {SONGS_DIR}")
    sys.exit(2)

  LIB_DIR.mkdir(parents=True, exist_ok=True)

  files: List[Path] = []
  for ext in CHO_EXTS:
    files.extend(SONGS_DIR.rglob(f"*{ext}"))
  files = sorted(set(files))

  log(f"Scanning {len(files)} song sheets under: {SONGS_DIR}")

  # song_uid -> accumulator
  by_song: Dict[str, Dict[str, Any]] = {}
  orphan = 0

  for i, p in enumerate(files, start=1):
    if i % 200 == 0:
      log(f"  ...parsed {i}/{len(files)}")
    text = p.read_text(encoding="utf-8", errors="replace")
    tags = parse_tag_block(text)

    song_uid = (tags.get("song_uid") or "").strip()
    uid      = (tags.get("uid") or "").strip()

    if not song_uid:
      orphan += 1
      continue

    title  = tags.get("title") or tags.get("t") or p.stem
    artist = tags.get("artist") or tags.get("a") or ""
    persona = tags.get("persona") or tags.get("version") or ""
    singer  = tags.get("singer") or ""
    duration = tags.get("duration") or ""
    tempo_i = safe_int(tags.get("tempo") or tags.get("bpm") or "")
    capo = tags.get("capo") or tags.get("ca") or ""
    key  = tags.get("key") or tags.get("k") or ""

    acc = by_song.get(song_uid)
    if not acc:
      acc = {
        "song_uid": song_uid,
        "title": title,
        "artist": artist,
        "personas": set(),
        "files": {},
        "sheet_uids": {},
        "meta_by_persona": {}
      }
      by_song[song_uid] = acc

    if persona:
      acc["personas"].add(persona)
      acc["files"][persona] = relpath(p)
      if uid:
        acc["sheet_uids"][persona] = uid

      acc["meta_by_persona"][persona] = {
        "uid": uid,
        "singer": singer,
        "duration": duration,
        "tempo": tempo_i,
        "capo": capo,
        "key": key
      }
    else:
      # no persona/version tag; store as a fallback "default"
      acc["files"][""] = relpath(p)
      if uid:
        acc["sheet_uids"][""] = uid
      acc["meta_by_persona"][""] = {
        "uid": uid,
        "singer": singer,
        "duration": duration,
        "tempo": tempo_i,
        "capo": capo,
        "key": key
      }

  # finalize canonical song list
  songs_out: List[Dict[str, Any]] = []
  for song_uid, acc in by_song.items():
    personas = sorted([p for p in acc["personas"] if p])
    # choose representative persona
    rep_persona = PREFERRED_PERSONA if PREFERRED_PERSONA in personas else (personas[0] if personas else "")
    rep_meta = acc["meta_by_persona"].get(rep_persona) or next(iter(acc["meta_by_persona"].values()), {})

    song = {
      "song_uid": song_uid,
      "uid": rep_meta.get("uid") or "",
      "title": acc["title"],
      "artist": acc["artist"],
      "personas": personas,
      "singer": rep_meta.get("singer") or "",
      "duration": rep_meta.get("duration") or "",
      "tempo": rep_meta.get("tempo"),
      "key": rep_meta.get("key") or "",
      "capo": rep_meta.get("capo") or "",
      "files": acc["files"],
      "sheet_uids": acc["sheet_uids"],  # NEW
    }
    songs_out.append(song)

  songs_out.sort(key=lambda s: (str(s.get("artist","")).lower(), str(s.get("title","")).lower()))

  # Load collections if present in existing library.index.json (so we preserve them)
  collections = []
  existing = OUT_LIB
  if existing.exists():
    try:
      old = json.loads(existing.read_text(encoding="utf-8"))
      if isinstance(old, dict) and isinstance(old.get("collections"), list):
        collections = old["collections"]
    except Exception:
      collections = []

  library_index = {
    "contract": "song_uid_v2",
    "version": 2,
    "songs": songs_out,
    "collections": collections
  }

  songs_index = {
    "contract": "song_uid_v2",
    "version": 2,
    "songCount": len(songs_out),
    "songs": songs_out
  }

  atomic_write_json(OUT_SONGS, songs_index)
  atomic_write_json(OUT_LIB, library_index)

  log(f"Done. Wrote:\n  {OUT_SONGS}\n  {OUT_LIB}\nCanonical songs: {len(songs_out)} | Orphan sheets: {orphan}")

if __name__ == "__main__":
  main()
