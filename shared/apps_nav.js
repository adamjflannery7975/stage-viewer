/*!
 * ChordPro Studio – Shared Apps Launcher (Modal)
 * File: /shared/apps_nav.js
 *
 * For apps living under /apps/:
 *   <script src="../shared/apps_nav.js"></script>
 *
 * Then wire your app button/logo to:
 *   window.CPSNav.open()
 *
 * Optional auto-bind (default): CPSNav.init({ bindTrigger:true, triggerSelector:'#brandHome' })
 */
(function(){
  'use strict';

  const NS = 'CPSNav';
  if (window[NS]) return; // prevent double-load

  function safeStr(v){ return (v == null) ? '' : String(v); }

  function findRepoRootFromPath(pathname){
    // GitHub Pages project sites like: /stage-viewer/apps/chordpro_edit.html
    // We want root: /stage-viewer
    const p = safeStr(pathname);
    const idx = p.toLowerCase().indexOf('/apps/');
    if (idx >= 0) return p.substring(0, idx) || '';
    // fallback: drop filename, then drop '/apps' if present
    return p.replace(/\/[^\/]*$/, '').replace(/\/apps$/i,'');
  }

  function getAppsIndexUrl(){
    try{
      const u = new URL(window.location.href);
      const root = findRepoRootFromPath(u.pathname);
      return u.origin + root + '/apps/index.html';
    }catch(e){
      return '../apps/index.html';
    }
  }

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
      'right:16px',
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
      'font-weight:800'
    ].join(';');

    const title = document.createElement('div');
    title.textContent = 'Apps';

    const actions = document.createElement('div');
    actions.style.cssText = 'display:flex; gap:8px; align-items:center;';

    const openTabBtn = document.createElement('button');
    openTabBtn.type = 'button';
    openTabBtn.textContent = 'Open';
    openTabBtn.title = 'Open Apps in this tab';
    openTabBtn.style.cssText = buttonCss();
    openTabBtn.addEventListener('click', () => { window.location.href = getAppsIndexUrl(); });

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.textContent = '✕';
    closeBtn.title = 'Close';
    closeBtn.style.cssText = buttonCss();
    closeBtn.addEventListener('click', close);

    actions.appendChild(openTabBtn);
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

    // Backdrop click closes (but clicking inside panel does not)
    modal.addEventListener('click', (e) => { if (e.target === modal) close(); });

    // ESC closes
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && isOpen()) close(); });

    return modal;
  }

  function isOpen(){
    const modal = document.getElementById('cpsAppsLauncherModal');
    return !!(modal && modal.style.display === 'block');
  }

  function open(){
    const modal = ensureModal();
    const frame = document.getElementById('cpsAppsLauncherFrame');
    if (frame) frame.src = getAppsIndexUrl();
    modal.style.display = 'block';
  }

  function close(){
    const modal = document.getElementById('cpsAppsLauncherModal');
    const frame = document.getElementById('cpsAppsLauncherFrame');
    if (frame) frame.src = 'about:blank';
    if (modal) modal.style.display = 'none';
  }

  function init(opts){
    const o = opts || {};
    const bindTrigger = (o.bindTrigger !== false);
    const selector = o.triggerSelector || '#brandHome';
    ensureModal();
    if (bindTrigger){
      const el = document.querySelector(selector);
      if (el){
        el.addEventListener('click', (e) => { e.preventDefault(); open(); });
        try{ el.style.cursor = 'pointer'; }catch(_e){}
      }
    }
  }

  window[NS] = { init, open, close, isOpen, getAppsIndexUrl };
})();
