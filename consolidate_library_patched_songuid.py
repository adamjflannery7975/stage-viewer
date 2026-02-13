#!/usr/bin/env python3
"""
ChordPro Studio - Library Consolidator (song_uid canonical)
----------------------------------------------------------

What this does:
- Scans ./songs/**/*.cho (and .pro/.chopro if present)
- Parses top tag block for: uid, song_uid, title, artist, persona/version, duration, tempo, capo, key
- Builds canonical SONG records keyed by song_uid (one "song" with multiple "sheets")
- Emits:
  - ./library/songs.index.json   (canonical songs)
  - ./library/library.index.json (songs + collections + metadata)

Why this exists:
- Your .cho files already contain BOTH:
    {uid: <sheet/version id>}
    {song_uid: <canonical song id shared across versions>}
  Setlist Builder needs a stable canonical id to prevent duplicates.
"""

from __future__ import annotations
import os, json, re, sys, time
from pathlib import Path
from typing import Dict, Any, List, Tuple

ROOT = Path(__file__).resolve().parent
SONGS_DIR = ROOT / "songs"
LIB_DIR   = ROOT / "library"
OUT_SONGS = LIB_DIR / "songs.index.json"
OUT_LIB   = LIB_DIR / "library.index.json"

CHO_EXTS = (".cho", ".chopro", ".pro")

TAG_LINE_RE = re.compile(r'^\s*\{([^}:]+)\s*:\s*(.*?)\}\s*$', re.I)

def log(msg: str):
    print(msg, flush=True)

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def parse_tag_block(text: str) -> Dict[str, str]:
    """
    Parse only the initial tag block (contiguous {tag: value} lines at the top).
    Stops when the first non-tag, non-blank line is encountered.
    """
    tags: Dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if s == "":
            # allow blank lines inside tag block
            continue
        m = TAG_LINE_RE.match(s)
        if not m:
            break
        k = m.group(1).strip().lower()
        v = m.group(2).strip()
        tags[k] = v
    return tags

def safe_int(v: str) -> int | None:
    try:
        return int(str(v).strip())
    except Exception:
        return None

def parse_duration_to_seconds(v: str) -> int | None:
    v = str(v or "").strip()
    if not v: return None
    # m:ss or mm:ss
    m = re.match(r'^(\d+)\s*:\s*(\d{1,2})$', v)
    if m:
        mins = int(m.group(1))
        secs = int(m.group(2))
        return mins*60 + secs
    # seconds
    i = safe_int(v)
    return i

def atomic_write_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)

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

    log(f"Scanning {len(files)} song files under: {SONGS_DIR}")

    by_song: Dict[str, Dict[str, Any]] = {}  # song_uid -> canonical entry with versions
    orphan_sheets: List[Dict[str, Any]] = []

    for idx, p in enumerate(files, start=1):
        if idx % 200 == 0:
            log(f"  ...parsed {idx}/{len(files)}")
        try:
            text = read_text(p)
        except Exception as e:
            log(f"WARN: failed read {p}: {e}")
            continue

        tags = parse_tag_block(text)

        sheet_uid = tags.get("uid", "").strip()
        song_uid  = tags.get("song_uid", "").strip()

        title  = tags.get("title") or tags.get("t") or p.stem
        artist = tags.get("artist") or tags.get("a") or ""

        persona = tags.get("persona") or tags.get("version") or ""
        singer  = tags.get("singer") or ""

        tempo = tags.get("tempo") or tags.get("bpm") or ""
        tempo_i = safe_int(tempo) if tempo else None

        dur_s = parse_duration_to_seconds(tags.get("duration",""))
        capo  = tags.get("capo") or tags.get("ca") or ""
        key   = tags.get("key") or tags.get("k") or ""

        rel = str(p.relative_to(ROOT)).replace("\\", "/")

        sheet = {
            "uid": sheet_uid or None,
            "song_uid": song_uid or None,
            "title": title,
            "artist": artist,
            "persona": persona,
            "singer": singer,
            "tempo": tempo_i,
            "duration_s": dur_s,
            "capo": capo,
            "key": key,
            "path": rel,
        }

        if not song_uid:
            # If a file lacks song_uid, we can't canonicalize it safely.
            orphan_sheets.append(sheet)
            continue

        entry = by_song.get(song_uid)
        if not entry:
            entry = {
                "song_uid": song_uid,
                "title": title,
                "artist": artist,
                "versions": [],      # sheets
                "personas": set(),   # computed
                "paths": [],         # convenience
            }
            by_song[song_uid] = entry

        entry["versions"].append(sheet)
        if persona:
            entry["personas"].add(persona)
        entry["paths"].append(rel)

    # finalize sets -> lists
    songs_out: List[Dict[str, Any]] = []
    for song_uid, entry in by_song.items():
        personas = sorted(list(entry["personas"]))
        entry["personas"] = personas
        # remove duplicates
        entry["paths"] = sorted(list(set(entry["paths"])))

        # choose a "display" representative: prefer first version
        rep = entry["versions"][0] if entry["versions"] else {}
        entry["duration_s"] = rep.get("duration_s")
        entry["tempo"] = rep.get("tempo")
        songs_out.append(entry)

    songs_out = sorted(songs_out, key=lambda x: (str(x.get("artist","")).lower(), str(x.get("title","")).lower()))

    # Load collections/setlists if they exist
    setlists_path = LIB_DIR / "setlists.json"
    setlists = None
    if setlists_path.exists():
        try:
            setlists = json.loads(setlists_path.read_text(encoding="utf-8"))
        except Exception as e:
            log(f"WARN: couldn't parse {setlists_path}: {e}")

    library_out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "songs_count": len(songs_out),
        "songs": songs_out,
    }
    if setlists is not None:
        library_out["setlists"] = setlists

    atomic_write_json(OUT_SONGS, songs_out)
    atomic_write_json(OUT_LIB, library_out)

    dt = time.time() - t0
    log(f"Done. Wrote:\n  {OUT_SONGS}\n  {OUT_LIB}\nSongs: {len(songs_out)} | Orphan sheets (missing song_uid): {len(orphan_sheets)} | {dt:.2f}s")

if __name__ == "__main__":
    main()
