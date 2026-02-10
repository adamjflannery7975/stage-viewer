#!/usr/bin/env python3
"""
Consolidate Library (ChordPro Studio)

Reads:
  - ./songs/*.cho
  - ./library/setlists.json

Writes (derived):
  - ./library/songs.index.json
  - ./library/library.index.json
  - ./library/consolidate.log.json

Safety:
  - DOES NOT modify .cho files
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TAG_RE = re.compile(r"^\s*\{([a-zA-Z0-9_\-]+)\s*:\s*(.*?)\}\s*$")


@dataclass
class SongFileMeta:
    uid: Optional[str]
    title: Optional[str]
    artist: Optional[str]
    persona: Optional[str]
    singer: Optional[str]
    duration: Optional[str]
    tempo: Optional[int]
    key: Optional[str]
    capo: Optional[int]


def now_iso_local() -> str:
    # Local timezone ISO string (includes offset)
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_int(value: str) -> Optional[int]:
    try:
        return int(str(value).strip())
    except Exception:
        return None


def parse_tags_from_cho(text: str) -> Dict[str, str]:
    """
    Parses top-level ChordPro tags of form {tag: value}.
    If a tag appears multiple times, first occurrence wins (stable).
    """
    tags: Dict[str, str] = {}
    for line in text.splitlines():
        m = TAG_RE.match(line)
        if not m:
            continue
        k = m.group(1).strip().lower()
        v = m.group(2).strip()
        if k not in tags:
            tags[k] = v
    return tags


def meta_from_tags(tags: Dict[str, str]) -> SongFileMeta:
    uid = tags.get("uid") or tags.get("song_uid")  # allow legacy tag name
    title = tags.get("title")
    artist = tags.get("artist")
    persona = tags.get("persona")
    singer = tags.get("singer")
    duration = tags.get("duration")
    tempo = parse_int(tags.get("tempo", "")) if "tempo" in tags else None
    key = tags.get("key")
    capo = parse_int(tags.get("capo", "")) if "capo" in tags else None

    return SongFileMeta(
        uid=uid,
        title=title,
        artist=artist,
        persona=persona,
        singer=singer,
        duration=duration,
        tempo=tempo,
        key=key,
        capo=capo,
    )


def relpath(from_dir: Path, to_path: Path) -> str:
    return os.path.relpath(to_path.resolve(), from_dir.resolve()).replace("\\", "/")


def load_setlists(setlists_path: Path) -> dict:
    """
    Supports BOTH formats:
      New: { version, updated, collections: [...] }
      Old: { version, setlists: [...] }  (auto-migrated into collections)
    """
    if not setlists_path.exists():
        return {"version": 1, "updated": now_iso_local(), "collections": []}

    try:
        data = json.loads(read_text(setlists_path))
        if not isinstance(data, dict):
            raise ValueError("setlists.json is not a JSON object")

        # New format
        if "collections" in data:
            if not isinstance(data["collections"], list):
                raise ValueError("setlists.json 'collections' must be an array")
            if "version" not in data:
                data["version"] = 1
            if "updated" not in data:
                data["updated"] = now_iso_local()
            return data

        # Old format -> migrate
        if "setlists" in data:
            if not isinstance(data["setlists"], list):
                raise ValueError("setlists.json 'setlists' must be an array")

            migrated = {
                "version": data.get("version", 1),
                "updated": now_iso_local(),
                "collections": []
            }

            for sl in data["setlists"]:
                migrated["collections"].append({
                    "id": sl.get("id") or sl.get("name") or "",
                    "type": "gig",
                    "name": sl.get("name") or sl.get("id") or "Unnamed",
                    "notes": sl.get("notes", ""),
                    "sets": sl.get("sets", [])
                })

            return migrated

        raise ValueError("setlists.json must contain either 'collections' or 'setlists'")

    except Exception as e:
        raise RuntimeError(f"Failed to parse {setlists_path}: {e}") from e


def consolidate(repo_root: Path, verbose: bool = True) -> Tuple[dict, dict, dict]:
    songs_dir = repo_root / "songs"
    library_dir = repo_root / "library"
    setlists_path = library_dir / "setlists.json"

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    started = now_iso_local()

    log = {
        "runId": run_id,
        "started": started,
        "repoRoot": str(repo_root.resolve()),
        "inputs": {
            "songsDir": str(songs_dir.resolve()),
            "setlists": str(setlists_path.resolve()),
        },
        "counts": {
            "choFilesFound": 0,
            "songsIndexed": 0,
            "uidsMissing": 0,
            "uidCollisionsPersona": 0,
            "setlists": 0,
            "setlistSongsReferenced": 0,
            "setlistMissingUids": 0,
        },
        "warnings": [],
        "errors": [],
    }

    if not songs_dir.exists():
        log["errors"].append(f"Missing songs folder: {songs_dir}")
        return {}, {}, log

    library_dir.mkdir(parents=True, exist_ok=True)

    # Load setlists (authoritative)
    try:
        setlists = load_setlists(setlists_path)
    except Exception as e:
        log["errors"].append(str(e))
        # IMPORTANT: match the "collections" shape used everywhere else
        setlists = {"version": 1, "updated": now_iso_local(), "collections": []}

    log["counts"]["setlists"] = len(setlists.get("collections", []))

    # Scan .cho files
    cho_files = sorted(songs_dir.rglob("*.cho"))
    log["counts"]["choFilesFound"] = len(cho_files)

    # Index by UID
    songs_by_uid: Dict[str, dict] = {}
    missing_uid_files: List[str] = []

    for f in cho_files:
        text = read_text(f)
        tags = parse_tags_from_cho(text)
        meta = meta_from_tags(tags)

        persona = (meta.persona or "").strip() or None
        uid = (meta.uid or "").strip() or None

        if not uid:
            missing_uid_files.append(relpath(repo_root, f))
            continue

        rec = songs_by_uid.get(uid)
        if rec is None:
            rec = {
                "uid": uid,
                "title": meta.title,
                "artist": meta.artist,
                "personas": [],
                "singer": meta.singer,
                "duration": meta.duration,
                "tempo": meta.tempo,
                "key": meta.key,
                "capo": meta.capo,
                "files": {},  # persona -> relative file path
            }
            songs_by_uid[uid] = rec

        # Fill gaps only (stable)
        for k, v in [
            ("title", meta.title),
            ("artist", meta.artist),
            ("singer", meta.singer),
            ("duration", meta.duration),
            ("tempo", meta.tempo),
            ("key", meta.key),
            ("capo", meta.capo),
        ]:
            if (rec.get(k) is None or rec.get(k) == "") and v not in (None, ""):
                rec[k] = v

        # Track persona -> file
        this_path = relpath(repo_root, f)
        if persona:
            if persona not in rec["personas"]:
                rec["personas"].append(persona)

            existing = rec["files"].get(persona)
            if existing and existing != this_path:
                log["counts"]["uidCollisionsPersona"] += 1
                log["warnings"].append(
                    f"UID {uid} has multiple files for persona '{persona}'. Keeping first: {existing}; ignoring: {this_path}"
                )
            else:
                rec["files"][persona] = this_path
        else:
            fallback_key = "_default"
            if fallback_key not in rec["files"]:
                rec["files"][fallback_key] = this_path
                log["warnings"].append(
                    f"UID {uid} file missing persona tag. Using fallback '_default': {this_path}"
                )

        if not meta.title:
            log["warnings"].append(f"UID {uid} missing {{title:}} in {this_path}")
        if not meta.artist:
            log["warnings"].append(f"UID {uid} missing {{artist:}} in {this_path}")

    log["counts"]["uidsMissing"] = len(missing_uid_files)
    if missing_uid_files:
        for p in missing_uid_files[:50]:
            log["warnings"].append(f"Missing UID tag in: {p}")
        if len(missing_uid_files) > 50:
            log["warnings"].append(f"...and {len(missing_uid_files) - 50} more files missing UID")

    # Build songs.index.json
    songs_list = sorted(
        songs_by_uid.values(),
        key=lambda r: ((r.get("title") or ""), (r.get("artist") or ""), r["uid"])
    )

    songs_index = {
        "generated": now_iso_local(),
        "songCount": len(songs_list),
        "songs": songs_list,
    }
    log["counts"]["songsIndexed"] = len(songs_list)

    # Validate setlists against known UIDs
    missing_uids: List[str] = []
    referenced = 0

    for col in setlists.get("collections", []):
        sets = col.get("sets", [])
        for s in sets:
            uids = s.get("songs", [])
            if isinstance(uids, list):
                for uid in uids:
                    referenced += 1
                    if uid not in songs_by_uid:
                        missing_uids.append(str(uid))

    log["counts"]["setlistSongsReferenced"] = referenced
    log["counts"]["setlistMissingUids"] = len(missing_uids)

    if missing_uids:
        uniq = sorted(set(missing_uids))
        for uid in uniq[:50]:
            log["warnings"].append(f"Setlists reference missing UID: {uid}")
        if len(uniq) > 50:
            log["warnings"].append(f"...and {len(uniq) - 50} more missing UIDs referenced by setlists")

    # Build library.index.json (master)
    library_index = {
        "version": 1,
        "lastConsolidated": now_iso_local(),
        "songs": songs_list,
        "collections": setlists.get("collections", []),
    }

    log["finished"] = now_iso_local()
    return songs_index, library_index, log


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidate ChordPro Studio library")
    parser.add_argument("--repo", default=".", help="Repo root folder (default: .)")
    parser.add_argument("--quiet", action="store_true", help="Less console output")
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    songs_index, library_index, log = consolidate(repo_root, verbose=not args.quiet)

    library_dir = repo_root / "library"
    out_songs = library_dir / "songs.index.json"
    out_library = library_dir / "library.index.json"
    out_log = library_dir / "consolidate.log.json"

    if log.get("errors"):
        print("❌ Consolidation failed:")
        for e in log["errors"]:
            print(" -", e)
        library_dir.mkdir(parents=True, exist_ok=True)
        out_log.write_text(json.dumps(log, indent=2), encoding="utf-8")
        print(f"Log written: {out_log}")
        return 1

    out_songs.write_text(json.dumps(songs_index, indent=2), encoding="utf-8")
    out_library.write_text(json.dumps(library_index, indent=2), encoding="utf-8")
    out_log.write_text(json.dumps(log, indent=2), encoding="utf-8")

    if not args.quiet:
        print("✅ Consolidation complete")
        print(f" - Songs indexed: {log['counts']['songsIndexed']}")
        print(f" - .cho files found: {log['counts']['choFilesFound']}")
        print(f" - Missing UID files: {log['counts']['uidsMissing']}")
        print(f" - Collections: {log['counts']['setlists']}")
        print(f" - Setlist missing UIDs: {log['counts']['setlistMissingUids']}")
        print("Outputs:")
        print(f" - {out_songs}")
        print(f" - {out_library}")
        print(f" - {out_log}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
