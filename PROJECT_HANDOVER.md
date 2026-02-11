# 📘 PROJECT_HANDOVER

## Project Name
**ChordPro Studio**  
Offline-first song editor, setlist builder, and stage viewer for live performance.

## Problem Statement
Live musicians need fast, readable, offline-capable song sheets with persona-specific layouts and reliable setlists. Existing tools are either cloud-dependent, visually cluttered, or not designed for live performance ergonomics.

## Vision
A self-contained, browser-based studio that:
- Works offline after first load
- Uses ChordPro as the single source of truth
- Separates editing, planning, and performance
- Scales cleanly from rehearsal to stage

## Applications
- **ChordPro Editor** – authoring, preview, PDF export, persona themes
- **Setlist Builder** – organise songs into sets/collections
- **Stage Viewer** – distraction-free performance UI

## Guiding Principles
- ChordPro is canonical
- Offline-first
- Shared theming
- Low cognitive load
- Explicit, readable code

## Current Status
Phase 1 complete and locked:
- Shared theme system
- Persona-aware rendering
- Chorus detection
- PWA + service worker
