/*!
 * ChordPro Studio – Shared Apps Launcher (Modal)
 * File: /shared/apps_nav.js
 *
 * Design goals:
 * - Single consistent entry point: click the app banner (e.g., #brandHome)
 * - Modal opens on the LEFT, near the clicked banner (anchored when possible)
 * - Clicking an app launches it in the TOP window (not inside the iframe)
 * - ESC / backdrop click closes
 *
 * For apps living under /apps/:
 *   <script src="../shared/apps_nav.js"></script>
 *   <script>window.CPSNav.init({ triggerSelector:'#brandHome' });</script>  // optional; default selector is #brandHome
 */
(function(){
  'use strict';

  const NS = 'CPSNav';
  if (window[NS]) return;

  function safeStr(v){ return (v == null) ? '' : String(v); }

  function findRepoRootFromPath(pathname){
    const p = safeStr(pathname);
    const idx = p.toLowerCase().indexOf('/apps/');
    if (idx >= 0) return p.substring(0, idx) || '';
    return p.replace(/\/[^\/]*$/, '').replace(/\/apps$/i,'');
  }

  function getRepoRootUrl(){
    const u = new URL(window.location.href);
    const root = findRepoRootFromPath(u.pathname);
    return u.origin + root;
  }

  function getAppsIndexUrl(){
    try{
      return getRepoRootUrl() + '/apps/index.html?launcher=1';
    }catch(e){
      return './index.html?launcher=1';
    }
  }

  function resolveAppUrl(href){
    // href in apps index may be like "apps/stage_viewer.html" or "./stage_viewer.html"
    const repoRoot = getRepoRootUrl();
    let h = safeStr(href).trim();
    if (!h) return repoRoot + '/apps/index.html';
    if (/^https?:\/\//i.test(h)) return h;
    // If it contains 'apps/' already, join to root
    if (h.toLowerCase().includes('apps/')) {
      // strip leading ./ or /
      h = h.replace(/^\.?\//,'').replace(/^\//,'');
      return repoRoot + '/' + h;
    }
    // Otherwise treat it as file under /apps/
    h = h.replace(/^\.?\//,'').replace(/^\//,'');
    return repoRoot + '/apps/' + h;
  }

  function clamp(n, lo, hi){ return Math.max(lo, Math.min(hi, n)); }

  function buttonCss(){
    return [
      'appearance:none',
      'border:1px solid rgba(255,255,255,.18)',
      'background:rgba(255,255,255,.06)',
      'color:var(--text, #f5f7ff)',
      'border-radius:10px',
      'padding:6px 10px',
      'cursor:pointer',
      'font-weight:800',
      'font-size:12px',
      'line-height:1'
    ].join(';');
  }

  function ensureModal(){
    let modal = document.getElementById('cpsAppsLauncherModal');
    if (modal) return modal;

    modal = document.createElement('div');
    modal.id = 'cpsAppsLauncherModal';
    modal.style.cssText = [
      'display:none',
      'position:fixed',
      'inset:0',
      'z-index:99999',
      'background:rgba(0,0,0,.62)',
      'backdrop-filter:blur(6px)',
      '-webkit-backdrop-filter:blur(6px)'
    ].join(';');

    const panel = document.createElement('div');
    panel.id = 'cpsAppsLauncherPanel';
    panel.style.cssText = [
      'position:absolute',
      'left:16px',
      'top:16px',
      'width:min(420px, calc(100vw - 32px))',
      'height:min(720px, calc(100vh - 32px))',
      'background:var(--panel, #171a21)',
      'border:1px solid var(--line, rgba(255,255,255,.12))',
      'border-radius:14px',
      'overflow:hidden',
      'box-shadow:0 20px 60px rgba(0,0,0,.55)'
    ].join(';');

    const head = document.createElement('div');
    head.style.cssText = [
      'display:flex',
      'align-items:center',
      'justify-content:space-between',
      'gap:10px',
      'padding:10px 12px',
      'border-bottom:1px solid var(--line, rgba(255,255,255,.12))',
      'color:var(--text, #f5f7ff)',
      'font-weight:900'
    ].join(';');

    const title = document.createElement('div');
    title.textContent = 'Apps';

    const actions = document.createElement('div');
    actions.style.cssText = 'display:flex; gap:8px; align-items:center;';

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.textContent = '✕';
    closeBtn.title = 'Close';
    closeBtn.style.cssText = buttonCss();
    closeBtn.addEventListener('click', close);

    actions.appendChild(closeBtn);
    head.appendChild(title);
    head.appendChild(actions);

    const frame = document.createElement('iframe');
    frame.id = 'cpsAppsLauncherFrame';
    frame.style.cssText = 'width:100%; height:calc(100% - 44px); border:0; background:transparent;';
    frame.setAttribute('title', 'Apps Launcher');

    panel.appendChild(head);
    panel.appendChild(frame);
    modal.appendChild(panel);
    document.body.appendChild(modal);

    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && isOpen()) close(); });

    return modal;
  }

  function isOpen(){
    const modal = document.getElementById('cpsAppsLauncherModal');
    return !!(modal && modal.style.display === 'block');
  }

  function positionPanel(anchorEl){
    const panel = document.getElementById('cpsAppsLauncherPanel');
    if (!panel) return;

    // Default left / top
    let left = 16, top = 16;

    try{
      if (anchorEl && anchorEl.getBoundingClientRect){
        const r = anchorEl.getBoundingClientRect();
        left = r.left;
        top = r.bottom + 8;
      }
    }catch(_e){}

    const vw = window.innerWidth || 800;
    const vh = window.innerHeight || 600;

    // panel sizes not known before render; approximate based on CSS
    const pw = Math.min(420, vw - 32);
    const ph = Math.min(720, vh - 32);

    left = clamp(left, 16, Math.max(16, vw - pw - 16));
    top  = clamp(top, 16, Math.max(16, vh - ph - 16));

    panel.style.left = left + 'px';
    panel.style.top = top + 'px';
  }

  function wireIframeClicks(){
    const frame = document.getElementById('cpsAppsLauncherFrame');
    if (!frame) return;

    const attach = () => {
      try{
        const doc = frame.contentDocument;
        if (!doc) return;

        // Ensure in "launcher mode" we don't show its own nav or links that trap you.
        doc.documentElement.classList.add('cps-launcher');

        // Intercept anchors + buttons with href or data-href
        const candidates = Array.from(doc.querySelectorAll('a[href], button[data-href], [data-href]'));
        candidates.forEach(el => {
          if (el.__cpsNavWired) return;
          el.__cpsNavWired = true;

          el.addEventListener('click', (e) => {
            // only left click / tap; allow ctrl/cmd click to open normally
            if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;

            const href = el.getAttribute('href') || el.getAttribute('data-href');
            if (!href) return;

            e.preventDefault();
            e.stopPropagation();

            navigateTo(resolveAppUrl(href));
          }, true);
        });
      }catch(_e){
        // If this fails, it's likely cross-origin (shouldn't be for your GH pages), ignore.
      }
    };

    frame.addEventListener('load', attach);
  }

  function open(anchorEl){
    const modal = ensureModal();
    const frame = document.getElementById('cpsAppsLauncherFrame');
    if (frame) frame.src = getAppsIndexUrl();
    modal.style.display = 'block';
    positionPanel(anchorEl || null);
    wireIframeClicks();
  }

  function close(){
    const modal = document.getElementById('cpsAppsLauncherModal');
    const frame = document.getElementById('cpsAppsLauncherFrame');
    if (frame) frame.src = 'about:blank';
    if (modal) modal.style.display = 'none';
  }

  function navigateTo(url){
    try{
      // Navigate the top-level window so we don't load inside iframe
      window.location.href = url;
    }finally{
      close();
    }
  }

  function init(opts){
    const o = opts || {};
    const selector = o.triggerSelector || '#brandHome';
    ensureModal();

    const el = document.querySelector(selector);
    if (el){
      el.addEventListener('click', (e) => { e.preventDefault(); open(el); });
      try{ el.style.cursor = 'pointer'; }catch(_e){}
    }
  }

  window[NS] = { init, open, close, isOpen, getAppsIndexUrl, navigateTo, resolveAppUrl };
})();
