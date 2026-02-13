# 🧱 ARCHITECTURE

## Repository Structure
/apps
  - chordpro_edit
  - setlist_builder
  - stage_viewer
/library
/songs
/shared
/serviceWorker.js

## Data Flow
Editor → .cho files → Setlist Builder → library.index.json → Stage Viewer

## Theme System
Centralised in shared/theme.js using CSS variables.
Applied consistently across Editor, Viewer, and PDF export.

## Offline Model
- App shell: cache-first
- Data: network-first with cache fallback
- Versioned caches

## LocalStorage Keys
- cps_theme
- cps_stageMode
- cps_persona
- cps_collection
- theme_settings
