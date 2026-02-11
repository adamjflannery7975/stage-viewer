#!/usr/bin/env node
/**
 * Rebuild Library Index (ChordPro Studio)
 *
 * Reads:
 *  - ./songs/*.cho
 *  - ./library/setlists.json
 *
 * Writes (derived):
 *  - ./library/songs.index.json
 *  - ./library/library.index.json
 *  - ./library/consolidate.log.json
 *
 * Notes:
 *  - Does NOT modify .cho files
 *  - Intentionally deterministic output ordering for clean diffs
 */

const fs = require("fs/promises");
const path = require("path");

const TAG_RE = /^\s*\{([a-zA-Z0-9_\-]+)\s*:\s*(.*?)\}\s*$/;

function nowIsoLocal() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");

  const year = d.getFullYear();
  const month = pad(d.getMonth() + 1);
  const day = pad(d.getDate());
  const hours = pad(d.getHours());
  const minutes = pad(d.getMinutes());
  const seconds = pad(d.getSeconds());

  const offsetMin = -d.getTimezoneOffset();
  const sign = offsetMin >= 0 ? "+" : "-";
  const abs = Math.abs(offsetMin);
  const offH = pad(Math.floor(abs / 60));
  const offM = pad(abs % 60);

  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}${sign}${offH}:${offM}`;
}

function toPosix(p) {
  return p.split(path.sep).join("/");
}

function parseIntSafe(v) {
  const n = parseInt(String(v).trim(), 10);
  return Number.isFinite(n) ? n : null;
}

function parseTagsFromCho(text) {
  // first occurrence wins (stable)
  const tags = {};
  const lines = text.split(/\r?\n/);
  for (const line of lines) {
    const m = line.match(TAG_RE);
    if (!m) continue;
    const k = String(m[1]).trim().toLowerCase();
    const v = String(m[2]).trim();
    if (!(k in tags)) tags[k] = v;
  }
  return tags;
}

function metaFromTags(tags) {
  const uid = tags.uid || tags.song_uid || null;
  const title = tags.title || null;
  const artist = tags.artist || null;
  const persona = tags.persona || null;
  const singer = tags.singer || null;
  const duration = tags.duration || null;
  const tempo = "tempo" in tags ? parseIntSafe(tags.tempo) : null;
  const key = tags.key || null;
  const capo = "capo" in tags ? parseIntSafe(tags.capo) : null;

  return { uid, title, artist, persona, singer, duration, tempo, key, capo };
}

async function readText(filePath) {
  return fs.readFile(filePath, { encoding: "utf-8" }).catch(async () => {
    // fallback to replace-ish behaviour
    const buf = await fs.readFile(filePath);
    return buf.toString("utf-8");
  });
}

async function exists(p) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function walk(dir, out = []) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      await walk(full, out);
    } else {
      out.push(full);
    }
  }
  return out;
}

async function loadSetlists(setlistsPath) {
  if (!(await exists(setlistsPath))) {
    return { version: 1, updated: nowIsoLocal(), collections: [] };
  }

  const raw = await readText(setlistsPath);
  let data;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    throw new Error(`Failed to parse ${setlistsPath}: ${e.message}`);
  }

  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new Error("setlists.json is not a JSON object");
  }

// New format
if ("collections" in data) {
  if (!Array.isArray(data.collections)) {
    throw new Error("setlists.json 'collections' must be an array");
  }
  if (!("version" in data)) data.version = 1;
  // IMPORTANT: do not inject timestamps here (keeps rebuild deterministic across machines/CI)
  return data;
}

  // Old format -> migrate
  if ("setlists" in data) {
    if (!Array.isArray(data.setlists)) {
      throw new Error("setlists.json 'setlists' must be an array");
    }
    const migrated = {
      version: data.version ?? 1,
      updated: nowIsoLocal(),
      collections: [],
    };

    for (const sl of data.setlists) {
      migrated.collections.push({
        id: sl.id || sl.name || "",
        type: "gig",
        name: sl.name || sl.id || "Unnamed",
        notes: sl.notes || "",
        sets: sl.sets || [],
      });
    }
    return migrated;
  }

  throw new Error("setlists.json must contain either 'collections' or 'setlists'");
}

async function main() {
  const repoRoot = process.argv.includes("--repo")
    ? path.resolve(process.argv[process.argv.indexOf("--repo") + 1] || ".")
    : path.resolve(".");

  const songsDir = path.join(repoRoot, "songs");
  const libraryDir = path.join(repoRoot, "library");
  const setlistsPath = path.join(libraryDir, "setlists.json");

  const runId = new Date().toISOString().replace(/[-:]/g, "").replace(/\..+/, "Z");
  const started = nowIsoLocal();

  const log = {
    runId,
    started,
    repoRoot,
    inputs: {
      songsDir,
      setlists: setlistsPath,
    },
    counts: {
      choFilesFound: 0,
      songsIndexed: 0,
      uidsMissing: 0,
      uidCollisionsPersona: 0,
      setlists: 0,
      setlistSongsReferenced: 0,
      setlistMissingUids: 0,
    },
    warnings: [],
    errors: [],
  };

  if (!(await exists(songsDir))) {
    log.errors.push(`Missing songs folder: ${songsDir}`);
    await fs.mkdir(libraryDir, { recursive: true });
    await fs.writeFile(path.join(libraryDir, "consolidate.log.json"), JSON.stringify(log, null, 2) + "\n", "utf-8");
    process.exit(1);
  }

  await fs.mkdir(libraryDir, { recursive: true });

  // Load setlists (authoritative)
  let setlists;
  try {
    setlists = await loadSetlists(setlistsPath);
  } catch (e) {
    log.errors.push(String(e.message || e));
    setlists = { version: 1, updated: nowIsoLocal(), collections: [] };
  }

  log.counts.setlists = Array.isArray(setlists.collections) ? setlists.collections.length : 0;

  // Scan .cho files
  const allFiles = await walk(songsDir);
  const choFiles = allFiles.filter((f) => f.toLowerCase().endsWith(".cho")).sort();
  log.counts.choFilesFound = choFiles.length;

  const songsByUid = new Map();
  const missingUidFiles = [];

  for (const f of choFiles) {
    const text = await readText(f);
    const tags = parseTagsFromCho(text);
    const meta = metaFromTags(tags);

    const persona = (meta.persona || "").trim() || null;
    const uid = (meta.uid || "").trim() || null;

    const rel = toPosix(path.relative(repoRoot, f));

    if (!uid) {
      missingUidFiles.push(rel);
      continue;
    }

    let rec = songsByUid.get(uid);
    if (!rec) {
      rec = {
        uid,
        title: meta.title,
        artist: meta.artist,
        personas: [],
        singer: meta.singer,
        duration: meta.duration,
        tempo: meta.tempo,
        key: meta.key,
        capo: meta.capo,
        files: {}, // persona -> relative path
      };
      songsByUid.set(uid, rec);
    }

    // Fill gaps only (stable)
    const fill = (k, v) => {
      if ((rec[k] === null || rec[k] === "" || typeof rec[k] === "undefined") && v !== null && v !== "") {
        rec[k] = v;
      }
    };
    fill("title", meta.title);
    fill("artist", meta.artist);
    fill("singer", meta.singer);
    fill("duration", meta.duration);
    fill("tempo", meta.tempo);
    fill("key", meta.key);
    fill("capo", meta.capo);

    if (persona) {
      if (!rec.personas.includes(persona)) rec.personas.push(persona);

      const existing = rec.files[persona];
      if (existing && existing !== rel) {
        log.counts.uidCollisionsPersona += 1;
        log.warnings.push(
          `UID ${uid} has multiple files for persona '${persona}'. Keeping first: ${existing}; ignoring: ${rel}`
        );
      } else {
        rec.files[persona] = rel;
      }
    } else {
      const fallbackKey = "_default";
      if (!rec.files[fallbackKey]) {
        rec.files[fallbackKey] = rel;
        log.warnings.push(`UID ${uid} file missing persona tag. Using fallback '_default': ${rel}`);
      }
    }

    if (!meta.title) log.warnings.push(`UID ${uid} missing {title:} in ${rel}`);
    if (!meta.artist) log.warnings.push(`UID ${uid} missing {artist:} in ${rel}`);
  }

  log.counts.uidsMissing = missingUidFiles.length;
  for (const p of missingUidFiles.slice(0, 50)) log.warnings.push(`Missing UID tag in: ${p}`);
  if (missingUidFiles.length > 50) log.warnings.push(`...and ${missingUidFiles.length - 50} more files missing UID`);

  // Deterministic sort
  const songsList = Array.from(songsByUid.values()).sort((a, b) => {
    const at = (a.title || "").localeCompare(b.title || "");
    if (at !== 0) return at;
    const aa = (a.artist || "").localeCompare(b.artist || "");
    if (aa !== 0) return aa;
    return String(a.uid).localeCompare(String(b.uid));
  });

  log.counts.songsIndexed = songsList.length;

  // Validate setlists against known UIDs
  let referenced = 0;
  const missing = [];

  for (const col of setlists.collections || []) {
    const sets = Array.isArray(col.sets) ? col.sets : [];
    for (const s of sets) {
      const uids = Array.isArray(s.songs) ? s.songs : [];
      for (const uid of uids) {
        referenced += 1;
        if (!songsByUid.has(String(uid))) missing.push(String(uid));
      }
    }
  }

  log.counts.setlistSongsReferenced = referenced;
  log.counts.setlistMissingUids = missing.length;

  const uniqMissing = Array.from(new Set(missing)).sort();
  for (const uid of uniqMissing.slice(0, 50)) log.warnings.push(`Setlists reference missing UID: ${uid}`);
  if (uniqMissing.length > 50) log.warnings.push(`...and ${uniqMissing.length - 50} more missing UIDs referenced`);

 const songsIndex = {
  songCount: songsList.length,
  songs: songsList,
};

const libraryIndex = {
  version: 1,
  songs: songsList,
  collections: setlists.collections || [],
};

  log.finished = nowIsoLocal();

  // Write outputs (pretty + newline for clean diffs)
  await fs.writeFile(path.join(libraryDir, "songs.index.json"), JSON.stringify(songsIndex, null, 2) + "\n", "utf-8");
  await fs.writeFile(path.join(libraryDir, "library.index.json"), JSON.stringify(libraryIndex, null, 2) + "\n", "utf-8");
  await fs.writeFile(path.join(libraryDir, "consolidate.log.json"), JSON.stringify(log, null, 2) + "\n", "utf-8");

  if (log.errors.length) process.exit(1);
}

main().catch((e) => {
  console.error("❌ Rebuild failed:", e);
  process.exit(1);
});
