# ChordPro Studio -- Editing & Publishing Workflow

## ⚡ 5-Line Summary (TL;DR)

1.  Pull latest changes (`git pull --rebase`)
2.  Edit songs using the web app and click **Save Back**
3.  Commit (pre-commit hook auto-rebuilds library indexes)
4.  Push (`git push`)
5.  Refresh Stage Viewer on iPad

------------------------------------------------------------------------

# Overview

ChordPro Studio is designed for:

-   **Desktop editing** (via the web apps)
-   **iPad viewing** (Stage Viewer)

Songs and setlists live in the Git repo.\
The Stage Viewer reads generated index files inside `/library`.

To keep everything consistent, this repo uses:

-   A **pre-commit hook** (local automation)
-   A **CI verification step** (remote enforcement)

This ensures the library index is always in sync with your `.cho` files.

------------------------------------------------------------------------

# One-Time Setup (Per Person)

## 1. Clone the Repo

``` bash
git clone git@github.com:adamjflannery/stage-viewer.git
cd stage-viewer
```

## 2. Ensure Node is Installed

``` bash
node -v
```

If missing (macOS + Homebrew):

``` bash
brew install node
```

## 3. Install the Git Hook (One Command)

``` bash
chmod +x tools/install-hooks.sh
./tools/install-hooks.sh
```

Optional test:

``` bash
.git/hooks/pre-commit
```

You should see:

    🔄 Rebuilding library index...
    ✅ Library index updated.

## 4. (Optional) Avoid SSH Passphrase Prompts

``` bash
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

------------------------------------------------------------------------

# Daily Editing Workflow

## Step 1 -- Pull Latest Changes

Before editing:

``` bash
git pull --rebase
```

(or use **Fetch origin** in GitHub Desktop)

------------------------------------------------------------------------

## Step 2 -- Edit in the Web App

-   Open ChordPro Studio locally
-   Edit your song or setlist
-   Click **Save Back**
-   Confirm the `.cho` file updates inside `/songs`

------------------------------------------------------------------------

## Step 3 -- Commit

Commit normally (GitHub Desktop or terminal).

The pre-commit hook automatically:

-   Rebuilds:
    -   `library/songs.index.json`
    -   `library/library.index.json`
-   Stages those files into the commit

You do **not** need to manually run the rebuild script.

------------------------------------------------------------------------

## Step 4 -- Push

``` bash
git push
```

CI will verify that the index is up to date.

------------------------------------------------------------------------

## Step 5 -- Refresh Stage Viewer

On iPad:

-   Refresh the page
-   If stale, clear website data for the viewer site

------------------------------------------------------------------------

# If CI Fails: "Library index is out of date"

Run locally:

``` bash
node tools/rebuild_library_index.js --repo .
git add library/songs.index.json library/library.index.json
git commit -m "chore: update library index"
git push
```

------------------------------------------------------------------------

# Troubleshooting

## `.DS_Store` Appears in Git

This repo ignores `.DS_Store`.\
If it was previously tracked:

``` bash
git rm --cached -r .DS_Store **/.DS_Store 2>/dev/null || true
git commit -m "chore: stop tracking .DS_Store"
git push
```

------------------------------------------------------------------------

## Pre-Commit Hook Not Running

Reinstall:

``` bash
./tools/install-hooks.sh
```

------------------------------------------------------------------------

# Design Intent

-   Editing happens via the apps
-   Save Back writes to local repo
-   Commit auto-rebuilds indexes
-   CI verifies integrity
-   Viewer consumes clean, deterministic library data

This keeps the system: - Offline-first - Backend-free - Deterministic -
Safe for multiple editors
