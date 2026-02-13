# ChordPro Studio -- Phase 2 UI & Viewer Change Log

This document tracks approved UI and behaviour changes to be implemented
in Phase 2.

------------------------------------------------------------------------

# Editor -- UI Improvements

## 1. Top Toolbar Refactor

### Problem

-   Toolbar is crowded and visually noisy
-   Button text wraps inconsistently
-   No clear grouping between document actions and app-level controls

### Changes Required

-   Prevent button text wrapping (single-line buttons only)
-   Reduce visual density (spacing + grouping)
-   Split toolbar into logical groups:

#### Group A -- Document Actions

-   New
-   Open
-   Save (.cho)
-   Save Back to File
-   New Version
-   PDF
-   Break
-   Blank Line

#### Group B -- App Controls

-   Apps (dropdown)
-   Mono
-   Theme (opens modal)
-   Text options

------------------------------------------------------------------------

## 2. Theme Controls → Modal (Shared Pattern)

### Problem

Theme controls permanently occupy vertical space.

### Changes Required

-   Move all theme controls into a pop-up modal (same style pattern as
    Viewer)
-   Modal triggered by **Theme** button
-   Collapse theme panel from main layout

### Theme Modal Contents

-   Style Profile
-   Background colour
-   Chord colour
-   Section colour
-   Chorus colour
-   Font size slider
-   Line spacing slider
-   Reset button
-   Font picker (moved here from toolbar)

------------------------------------------------------------------------

## 3. Font Picker Relocation

### Problem

Font control is currently in toolbar, increasing clutter.

### Change

-   Move font picker into Theme modal
-   Treat font selection as part of visual theme configuration

------------------------------------------------------------------------

## 4. Apps Button Dropdown

### Problem

Apps navigation currently separate and not scalable.

### Change

-   Convert "Apps" button into dropdown menu
-   Dropdown lists:
    -   Editor
    -   Viewer
    -   Gig Builder
    -   Catalog Manager
-   Future: may become central home page

------------------------------------------------------------------------

# Viewer -- Behaviour Fixes

## 1. Hide Page Break Tag

### Problem

Viewer displays Page Break tag intended only for PDF export in Editor.

### Change

-   Viewer must ignore page break directive
-   Page Break remains functional for PDF export only
-   No visible artefact in Viewer mode

------------------------------------------------------------------------

# Shared Feature Enhancement

## Theme Editing in Viewer

### Requirement

-   Add same Theme modal to Viewer
-   Theme editing available in both Editor and Viewer
-   Consistent theme engine across apps

------------------------------------------------------------------------

# Design Principles for Phase 2

-   Reduce cognitive load
-   Separate editing tools from application controls
-   Minimise permanent UI elements
-   Move advanced controls into modals
-   Maintain consistent theme engine across all apps
-   Ensure Viewer remains clean and performance-focused

------------------------------------------------------------------------

# Status

These changes are approved for implementation in Phase 2.
