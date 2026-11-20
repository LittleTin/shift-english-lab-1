/* Public client key only. Do not place administrator or service-role credentials here. */
(() => {
  const allowed = location.origin === 'https://littletin.github.io' &&
    (location.pathname === '/shift-english-lab-1' || location.pathname.startsWith('/shift-english-lab-1/'));
  window.SHIFT_SYNC_CONFIG = Object.freeze(allowed ? {
    url: 'https://xcyokfbdydcuijymybqq.supabase.co',
    publishableKey: 'sb_publishable_ZAPbgOWx99tVBtAlkPFXxA_GiZkhKe2'
  } : {url: '', publishableKey: ''});
})();
