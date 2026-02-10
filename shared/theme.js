/* ChordPro Studio — Shared Theme Engine
   - per-device (localStorage)
   - shared across apps (same GitHub Pages origin)
   - separates UI theme (light/dark) from ChordPro colours
*/

(function () {
  const LS_PREFIX = "cps_theme_";

  const DEFAULTS = {
    // UI
    uiMode: "dark", // "dark" | "light"

    // ChordPro palette (applies to preview + viewer)
    cp_bg_dark: "#0b0d12",
    cp_bg_light: "#ffffff",

    cp_lyrics_dark: "#ffffff",
    cp_lyrics_light: "#000000",

    cp_chords_dark: "#00ffff",
    cp_chords_light: "#0056b3",

    cp_section_dark: "#ffff00",
    cp_section_light: "#d00000",

    cp_chorus_dark: "#ff6b6b",
    cp_chorus_light: "#d00000",

    // Typography
    cp_font_size: "18px",
    cp_line_height: "1.45",
  };

  function load(key) {
    const v = localStorage.getItem(LS_PREFIX + key);
    return v === null ? DEFAULTS[key] : v;
  }

  function save(key, value) {
    localStorage.setItem(LS_PREFIX + key, String(value));
  }

  function cssVar(name, value) {
    document.documentElement.style.setProperty(name, value);
  }

  function getUiMode() {
    return load("uiMode");
  }

  function applyUiMode(mode) {
    const m = (mode === "light") ? "light" : "dark";
    document.body.classList.toggle("light", m === "light");
    save("uiMode", m);
    applyChordProTheme(); // ensure palette matches mode
  }

  function applyChordProTheme() {
    const mode = getUiMode();

    // pick correct palette for mode
    cssVar("--cp-bg", load(mode === "light" ? "cp_bg_light" : "cp_bg_dark"));
    cssVar("--cp-lyrics", load(mode === "light" ? "cp_lyrics_light" : "cp_lyrics_dark"));
    cssVar("--cp-chords", load(mode === "light" ? "cp_chords_light" : "cp_chords_dark"));
    cssVar("--cp-section", load(mode === "light" ? "cp_section_light" : "cp_section_dark"));
    cssVar("--cp-chorus", load(mode === "light" ? "cp_chorus_light" : "cp_chorus_dark"));

    cssVar("--cp-font-size", load("cp_font_size"));
    cssVar("--cp-line-height", load("cp_line_height"));
  }

  function setChordPro(keyBase, value) {
    // keyBase examples: "cp_chords_dark", "cp_chords_light", "cp_font_size"
    save(keyBase, value);
    applyChordProTheme();
  }

  function getAll() {
    const out = {};
    Object.keys(DEFAULTS).forEach(k => out[k] = load(k));
    return out;
  }

  // Expose a tiny API
  window.CPS_THEME = {
    defaults: DEFAULTS,
    getAll,
    getUiMode,
    applyUiMode,
    applyChordProTheme,
    setChordPro,
    load,
    save,
  };

  // Apply immediately on load
  document.addEventListener("DOMContentLoaded", () => {
    applyUiMode(getUiMode());
    applyChordProTheme();
  });
})();
