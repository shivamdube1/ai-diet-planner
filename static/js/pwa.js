/* ============================================================
   NutriAI PWA Manager — pwa.js
   Handles:
     • Service Worker registration + update detection
     • Install prompt (custom "Add to Home Screen" banner)
     • Online / Offline status banner
     • Push notification subscription
   ============================================================ */

(function () {
  'use strict';

  // ── 1. Service Worker Registration ──────────────────────────
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
      try {
        const reg = await navigator.serviceWorker.register('/sw.js', {
          scope: '/'
        });
        console.log('[PWA] Service Worker registered, scope:', reg.scope);

        // ── Detect SW update available ──
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              showUpdateBanner(newWorker);
            }
          });
        });

        // ── Check for existing update ──
        reg.update();

      } catch (err) {
        console.warn('[PWA] Service Worker registration failed:', err);
      }
    });
  }

  // ── 2. Install Prompt (Add to Home Screen) ──────────────────
  let deferredInstallPrompt = null;

  const navBtn = document.getElementById('nav-install-btn');
  const navItem = document.getElementById('nav-install-item');

  // Detect standalone mode
  const isInStandaloneMode = () => 
    ('standalone' in window.navigator) && (window.navigator.standalone) || 
    window.matchMedia('(display-mode: standalone)').matches;

  // Show the Install button in nav if not already installed
  if (navItem && navBtn && !isInStandaloneMode()) {
    navItem.classList.remove('d-none');
    
    // Default click handler (handles both native prompt and manual fallback)
    navBtn.onclick = async (e) => {
      e.preventDefault();
      if (deferredInstallPrompt) {
        // Native prompt available
        navItem.classList.add('d-none'); // immediately hide
        try {
          deferredInstallPrompt.prompt();
          const { outcome } = await deferredInstallPrompt.userChoice;
          console.log('[PWA] Nav install outcome:', outcome);
          if (outcome === 'accepted') {
            showInstallationProgress();
          } else if (outcome === 'dismissed') {
            navItem.classList.remove('d-none');
          }
        } catch (err) {
          console.warn('[PWA] Prompt failed', err);
          navItem.classList.remove('d-none');
        }
        deferredInstallPrompt = null;
      } else {
        // Native prompt not available (iOS, Safari, Firefox, or insecure HTTP)
        showManualInstallInstructions();
      }
    };
  }

  function showManualInstallInstructions() {
    if (document.getElementById('pwa-manual-modal')) return;

    const isIos = /iphone|ipad|ipod/.test(window.navigator.userAgent.toLowerCase());
    const modal = document.createElement('div');
    modal.id = 'pwa-manual-modal';
    
    let instructions = isIos 
      ? `To install NutriAI, tap the <strong style="color:#fff;">Share</strong> icon at the bottom of your screen, then select <strong style="color:#fff;">Add to Home Screen</strong>.`
      : `To install NutriAI on this device/browser, please use your browser's menu (⋮) and select <strong style="color:#fff;">Install App</strong> or <strong style="color:#fff;">Add to Home Screen</strong>. Make sure you are using a secure connection (HTTPS).`;

    modal.innerHTML = `
      <div style="position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.6); z-index:10000; display:flex; align-items:center; justify-content:center; padding:20px;">
        <div style="background:#1e293b; padding:24px; border-radius:12px; max-width:400px; width:100%; box-shadow:0 10px 25px rgba(0,0,0,0.5); border:1px solid #334155; position:relative;">
          <h4 style="color:#f8fafc; margin-top:0; margin-bottom:15px; font-family:'Playfair Display', serif;">Install NutriAI</h4>
          <p style="color:#cbd5e1; font-size:0.95rem; line-height:1.6; margin-bottom:20px;">${instructions}</p>
          <button id="pwa-manual-close" style="background:#16a34a; color:#fff; border:none; padding:10px 16px; border-radius:6px; font-weight:600; cursor:pointer; width:100%; transition:background 0.2s;">Got it!</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    
    const closeBtn = document.getElementById('pwa-manual-close');
    closeBtn.onmouseover = () => closeBtn.style.background = '#15803d';
    closeBtn.onmouseout = () => closeBtn.style.background = '#16a34a';
    closeBtn.onclick = () => modal.remove();
  }

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredInstallPrompt = e;

    // Don't show if already installed or dismissed recently
    if (localStorage.getItem('pwa-install-dismissed')) return;

    // Small delay so page has loaded
    setTimeout(() => showInstallBanner(), 3000);
  });

  window.addEventListener('appinstalled', () => {
    deferredInstallPrompt = null;
    hideInstallBanner();
    hideInstallationProgress(); // clear the fake progress bar overlay
    const navItem = document.getElementById('nav-install-item');
    if (navItem) navItem.classList.add('d-none');
    localStorage.setItem('pwa-installed', 'true');
    console.log('[PWA] App installed!');
  });

  function showInstallBanner() {
    if (document.getElementById('pwa-install-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'pwa-install-banner';
    banner.innerHTML = `
      <div class="pwa-banner-content">
        <div class="pwa-banner-left">
          <img src="/static/icon-192.png" alt="NutriAI" class="pwa-banner-icon">
          <div class="pwa-banner-text">
            <strong>Install NutriAI</strong>
            <span>Add to your home screen for offline access</span>
          </div>
        </div>
        <div class="pwa-banner-actions">
          <button id="pwa-install-btn" class="pwa-btn-install">
            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path d="M12 16l-4-4h3V4h2v8h3l-4 4z"/><path d="M20 18H4v2h16v-2z"/>
            </svg>
            Install
          </button>
          <button id="pwa-dismiss-btn" class="pwa-btn-dismiss" aria-label="Dismiss">✕</button>
        </div>
      </div>
    `;

    document.body.appendChild(banner);

    // Animate in
    requestAnimationFrame(() => banner.classList.add('pwa-banner-visible'));

    document.getElementById('pwa-install-btn').addEventListener('click', async () => {
      if (!deferredInstallPrompt) return;
      hideInstallBanner();
      deferredInstallPrompt.prompt();
      const { outcome } = await deferredInstallPrompt.userChoice;
      console.log('[PWA] Install prompt outcome:', outcome);
      if (outcome === 'accepted') {
        showInstallationProgress();
      }
      deferredInstallPrompt = null;
    });

    document.getElementById('pwa-dismiss-btn').addEventListener('click', () => {
      hideInstallBanner();
      localStorage.setItem('pwa-install-dismissed', Date.now());
    });
  }

  function hideInstallBanner() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner) {
      banner.classList.remove('pwa-banner-visible');
      setTimeout(() => banner.remove(), 400);
    }
  }

  // ==== NEW: Simulated Installation Progress UI ====
  let installProgressInterval = null;
  function showInstallationProgress() {
    if (document.getElementById('pwa-install-progress-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'pwa-install-progress-overlay';
    overlay.innerHTML = `
      <div class="install-progress-box">
        <h3 id="install-title">Minting your App Space...</h3>
        <p id="install-subtitle">This might take a moment.</p>
        <div class="install-bar-track">
          <div class="install-bar-fill" id="install-fill"></div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    // animate in
    requestAnimationFrame(() => overlay.style.opacity = '1');

    const fill = document.getElementById('install-fill');
    const title = document.getElementById('install-title');
    const subtitle = document.getElementById('install-subtitle');
    let percent = 0;

    installProgressInterval = setInterval(() => {
      percent += Math.random() * 3 + 1; // 1-4% at a time
      if (percent > 99) percent = 99; // hang at 99% until real appinstalled event
      
      fill.style.width = percent + '%';
      
      if (percent > 20 && percent < 60) {
        title.innerText = 'Downloading assets...';
      } else if (percent >= 60 && percent < 90) {
        title.innerText = 'Optimizing for offline use...';
      } else if (percent >= 90) {
        title.innerText = 'Finalizing installation...';
        subtitle.innerText = 'Almost ready! Waiting for verification...';
      }
    }, 400); // update every 400ms
  }

  function hideInstallationProgress() {
    const overlay = document.getElementById('pwa-install-progress-overlay');
    if (overlay) {
      clearInterval(installProgressInterval);
      
      const fill = document.getElementById('install-fill');
      const title = document.getElementById('install-title');
      const subtitle = document.getElementById('install-subtitle');
      if (fill) fill.style.width = '100%';
      if (title) title.innerText = 'Successfully Installed! ✓';
      if (subtitle) subtitle.innerText = 'You can now launch the app from your home screen.';

      setTimeout(() => {
        overlay.style.opacity = '0';
        setTimeout(() => overlay.remove(), 600);
      }, 1500);
    }
  }


  // ── 3. Update Available Banner ───────────────────────────────
  function showUpdateBanner(newWorker) {
    if (document.getElementById('pwa-update-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'pwa-update-banner';
    banner.innerHTML = `
      <div class="pwa-update-content">
        <span>🚀 NutriAI has been updated!</span>
        <button id="pwa-reload-btn" class="pwa-btn-update">Reload to apply</button>
        <button id="pwa-update-dismiss" class="pwa-btn-dismiss" aria-label="Dismiss">✕</button>
      </div>
    `;
    document.body.appendChild(banner);
    requestAnimationFrame(() => banner.classList.add('pwa-banner-visible'));

    document.getElementById('pwa-reload-btn').addEventListener('click', () => {
      newWorker.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    });

    document.getElementById('pwa-update-dismiss').addEventListener('click', () => {
      banner.classList.remove('pwa-banner-visible');
      setTimeout(() => banner.remove(), 400);
    });
  }

  // ── 4. Online / Offline Status Banner ───────────────────────
  let offlineBanner = null;

  function createOfflineBanner() {
    if (offlineBanner) return;
    offlineBanner = document.createElement('div');
    offlineBanner.id = 'pwa-offline-banner';
    offlineBanner.innerHTML = `
      <span class="pwa-offline-dot"></span>
      <span>You're offline — some features may be limited</span>
    `;
    document.body.appendChild(offlineBanner);
    requestAnimationFrame(() => offlineBanner.classList.add('pwa-banner-visible'));
  }

  function removeOfflineBanner() {
    if (!offlineBanner) return;
    offlineBanner.innerHTML = `
      <span class="pwa-online-dot"></span>
      <span>Back online! ✓</span>
    `;
    offlineBanner.classList.add('pwa-back-online');
    setTimeout(() => {
      offlineBanner?.classList.remove('pwa-banner-visible');
      setTimeout(() => { offlineBanner?.remove(); offlineBanner = null; }, 400);
    }, 2500);
  }

  window.addEventListener('online',  removeOfflineBanner);
  window.addEventListener('offline', createOfflineBanner);

  // Check initial state
  if (!navigator.onLine) {
    setTimeout(createOfflineBanner, 500);
  }


  // ── 5. Inject PWA Styles ─────────────────────────────────────
  const style = document.createElement('style');
  style.textContent = `
    /* ── Install Banner ── */
    #pwa-install-banner {
      position: fixed;
      bottom: 0; left: 0; right: 0;
      z-index: 10000;
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      border-top: 1px solid rgba(22,163,74,0.4);
      padding: 12px 16px;
      transform: translateY(100%);
      transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: 0 -4px 24px rgba(0,0,0,0.4);
    }
    #pwa-install-banner.pwa-banner-visible {
      transform: translateY(0);
    }
    .pwa-banner-content {
      display: flex;
      align-items: center;
      justify-content: space-between;
      max-width: 700px;
      margin: 0 auto;
      gap: 12px;
    }
    .pwa-banner-left {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;
    }
    .pwa-banner-icon {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      flex-shrink: 0;
    }
    .pwa-banner-text {
      display: flex;
      flex-direction: column;
    }
    .pwa-banner-text strong {
      color: #f1f5f9;
      font-size: 0.9rem;
      font-weight: 600;
    }
    .pwa-banner-text span {
      color: #94a3b8;
      font-size: 0.78rem;
    }
    .pwa-banner-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }
    .pwa-btn-install {
      display: flex;
      align-items: center;
      gap: 6px;
      background: linear-gradient(135deg, #16a34a, #15803d);
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 8px 16px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      white-space: nowrap;
    }
    .pwa-btn-install:hover {
      background: linear-gradient(135deg, #15803d, #166534);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(22,163,74,0.4);
    }
    .pwa-btn-dismiss {
      background: transparent;
      border: none;
      color: #64748b;
      font-size: 1rem;
      cursor: pointer;
      padding: 6px 8px;
      border-radius: 6px;
      transition: color 0.2s, background 0.2s;
    }
    .pwa-btn-dismiss:hover {
      color: #f1f5f9;
      background: rgba(255,255,255,0.08);
    }

    /* ── Update Banner ── */
    #pwa-update-banner {
      position: fixed;
      top: 0; left: 0; right: 0;
      z-index: 10001;
      background: linear-gradient(135deg, #1d4ed8, #1e40af);
      padding: 10px 16px;
      transform: translateY(-100%);
      transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    }
    #pwa-update-banner.pwa-banner-visible {
      transform: translateY(0);
    }
    .pwa-update-content {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      color: #fff;
      font-size: 0.88rem;
      max-width: 700px;
      margin: 0 auto;
    }
    .pwa-btn-update {
      background: rgba(255,255,255,0.2);
      border: 1px solid rgba(255,255,255,0.4);
      color: #fff;
      border-radius: 6px;
      padding: 6px 14px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }
    .pwa-btn-update:hover {
      background: rgba(255,255,255,0.3);
    }

    /* ── Offline Banner ── */
    #pwa-offline-banner {
      position: fixed;
      bottom: 0; left: 0; right: 0;
      z-index: 9999;
      background: #1e293b;
      border-top: 1px solid #334155;
      padding: 10px 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      color: #94a3b8;
      font-size: 0.85rem;
      transform: translateY(100%);
      transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }
    #pwa-offline-banner.pwa-banner-visible {
      transform: translateY(0);
    }
    #pwa-offline-banner.pwa-back-online {
      background: #14532d;
      color: #86efac;
      border-top-color: #16a34a;
    }
    .pwa-offline-dot {
      width: 8px; height: 8px;
      background: #f87171;
      border-radius: 50%;
      animation: pwa-pulse 1.5s infinite;
    }
    .pwa-online-dot {
      width: 8px; height: 8px;
      background: #4ade80;
      border-radius: 50%;
    }
    @keyframes pwa-pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50%       { opacity: 0.5; transform: scale(1.3); }
    }

    @media (max-width: 480px) {
      .pwa-banner-text span { display: none; }
      .pwa-btn-install { padding: 8px 12px; }
    }

    /* ── Progress Overlay ── */
    #pwa-install-progress-overlay {
      position: fixed; inset: 0; z-index: 10005;
      background: rgba(15, 23, 42, 0.9);
      backdrop-filter: blur(8px);
      display: flex; align-items: center; justify-content: center;
      opacity: 0; transition: opacity 0.4s ease;
    }
    .install-progress-box {
      background: #1e293b; border: 1px solid #334155;
      padding: 30px; border-radius: 16px; width: 90%; max-width: 400px;
      text-align: center; color: #fff;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5);
    }
    .install-progress-box h3 {
      font-family: 'Playfair Display', serif; font-size: 1.3rem; margin: 0 0 8px; color: #f8fafc;
    }
    .install-progress-box p {
      font-size: 0.9rem; color: #94a3b8; margin: 0 0 24px;
    }
    .install-bar-track {
      width: 100%; height: 8px; background: rgba(0,0,0,0.3);
      border-radius: 10px; overflow: hidden;
    }
    .install-bar-fill {
      height: 100%; width: 0%; background: linear-gradient(90deg, #22c55e, #4ade80);
      transition: width 0.4s ease; border-radius: 10px;
    }
  `;
  document.head.appendChild(style);

})();
