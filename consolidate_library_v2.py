#!/usr/bin/env python3
"""
consolidate_library_v2.py
------------------------

Contract B builder (canonical song_uid) that writes VERSIONED outputs only:

  library/songs.index.v2.json
  library/library.index.v2.json

It leaves legacy files untouched:
  library/songs.index.json
  library/library.index.json

Assumptions:
- Repo root contains: ./songs/ and ./library/
- Song sheets are .cho (also supports .pro/.chopro)
- Top tag block contains {uid: ...} and {song_uid: ...}
- persona selection uses {persona: ...} or {version: ...}

Output schema:
songs.index.v2.json:
{
  "version": 2,
  "contract": "song_uid_v2",
  "generated_at": "ISO",
  "songCount": 339,
  "songs": [ canonicalSong, ... ]
}

library.index.v2.json:
{
  "version": 2,
  "contract": "song_uid_v2",
  "generated_at": "ISO",
  "songs": [ canonicalSong, ... ],
  "collections": <copied from legacy library.index.json if present>
}

canonicalSong:
{
  "song_uid": "song-...",
  "uid": "uid-...",                  # representative sheet uid
  "title": "...",
  "artist": "...",
  "personas": ["Adam","Pete"],
  "singer": "...",
  "duration": "3:35",
  "tempo": 135,
  "key": "A",
  "capo": "2",
  "files": { "Adam":"songs/..cho", "Pete":"songs/..cho" },
  "sheet_uids": { "Adam":"uid-..", "Pete":"uid-.." }
}
"""

from __future__ import annotations
import json, re, sys, time
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parent
SONGS_DIR = ROOT / "songs"
LIB_DIR   = ROOT / "library"
OUT_SONGS_V2 = LIB_DIR / "songs.index.v2.json"
OUT_LIB_V2   = LIB_DIR / "library.index.v2.json"

CHO_EXTS = (".cho", ".chopro", ".pro")
TAG_LINE_RE = re.compile(r'^\s*\{([^}:]+)\s*:\s*(.*?)\}\s*$', re.I)

PREFERRED_PERSONA = "Adam"  # used only to pick representative fields

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
    t0 = time.time()

    if not SONGS_DIR.exists():
        log(f"ERROR: songs folder not found: {SONGS_DIR}")
        sys.exit(2)

    LIB_DIR.mkdir(parents=True, exist_ok=True)

    files: List[Path] = []
    for ext in CHO_EXTS:
        files.extend(SONGS_DIR.rglob(f"*{ext}"))
    files = sorted(set(files))

    log(f"Scanning {len(files)} song sheets under: {SONGS_DIR}")

    by_song: Dict[str, Dict[str, Any]] = {}
    orphan = 0

    for i, p in enumerate(files, start=1):
        if i % 200 == 0:
            log(f"  ...parsed {i}/{len(files)}")
        text = p.read_text(encoding="utf-8", errors="replace")
        tags = parse_tag_block(text)

        song_uid = (tags.get("song_uid") or "").strip()
        uid = (tags.get("uid") or "").strip()
        if not song_uid:
            orphan += 1
            continue

        title = tags.get("title") or tags.get("t") or p.stem
        artist = tags.get("artist") or tags.get("a") or ""
        persona = tags.get("persona") or tags.get("version") or ""
        singer = tags.get("singer") or ""
        duration = tags.get("duration") or ""
        tempo = safe_int(tags.get("tempo") or tags.get("bpm") or "")
        capo = tags.get("capo") or tags.get("ca") or ""
        key = tags.get("key") or tags.get("k") or ""

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

        # Maintain canonical title/artist if first sheet had them; ignore later drift
        if persona:
            acc["personas"].add(persona)
            acc["files"][persona] = relpath(p)
            if uid:
                acc["sheet_uids"][persona] = uid
            acc["meta_by_persona"][persona] = {
                "uid": uid,
                "singer": singer,
                "duration": duration,
                "tempo": tempo,
                "capo": capo,
                "key": key
            }
        else:
            # fallback bucket if persona isn't set
            acc["files"][""] = relpath(p)
            if uid:
                acc["sheet_uids"][""] = uid
            acc["meta_by_persona"][""] = {
                "uid": uid,
                "singer": singer,
                "duration": duration,
                "tempo": tempo,
                "capo": capo,
                "key": key
            }

    # Build canonical list
    songs_out: List[Dict[str, Any]] = []
    for song_uid, acc in by_song.items():
        personas = sorted([p for p in acc["personas"] if p])

        rep_persona = PREFERRED_PERSONA if PREFERRED_PERSONA in personas else (personas[0] if personas else "")
        rep_meta = acc["meta_by_persona"].get(rep_persona) or next(iter(acc["meta_by_persona"].values()), {})

        songs_out.append({
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
            "sheet_uids": acc["sheet_uids"]
        })

    songs_out.sort(key=lambda s: (str(s.get("artist","")).lower(), str(s.get("title","")).lower()))

    # Carry forward collections from legacy library.index.json if present
    legacy_lib = LIB_DIR / "library.index.json"
    collections = []
    if legacy_lib.exists():
        try:
            old = json.loads(legacy_lib.read_text(encoding="utf-8"))
            if isinstance(old, dict) and isinstance(old.get("collections"), list):
                collections = old["collections"]
        except Exception:
            collections = []

    iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    songs_index_v2 = {
        "version": 2,
        "contract": "song_uid_v2",
        "generated_at": iso,
        "songCount": len(songs_out),
        "songs": songs_out
    }
    lib_index_v2 = {
        "version": 2,
        "contract": "song_uid_v2",
        "generated_at": iso,
        "songs": songs_out,
        "collections": collections
    }

    atomic_write_json(OUT_SONGS_V2, songs_index_v2)
    atomic_write_json(OUT_LIB_V2, lib_index_v2)

    dt = time.time() - t0
    log(f"Done. Wrote:\n  {OUT_SONGS_V2}\n  {OUT_LIB_V2}\nCanonical songs: {len(songs_out)} | Orphan sheets: {orphan} | {dt:.2f}s")

if __name__ == "__main__":
    main()
