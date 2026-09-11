// This standalone preview is intentionally independent of game state and the game bundle.
if (new URLSearchParams(location.search).get('shuttlePreview') === '1') {
  const insertPreview = () => {
    const heading = document.querySelector('.shuttle-preview > h1');
    if (!heading) return false;
    if (document.getElementById('moweyds-ring-preview')) return true;
    const frame = document.createElement('iframe');
    frame.id = 'moweyds-ring-preview';
    frame.title = '모웨이드 파워 링 건물 배치 미리보기';
    frame.src = '/previews/moweyds-ring/index.html';
    frame.style.cssText = 'display:block;width:100%;height:850px;border:1px solid #334155;border-radius:12px;margin:0 0 24px';
    heading.after(frame);
    return true;
  };
  if (!insertPreview()) {
    const observer = new MutationObserver(() => {
      if (insertPreview()) observer.disconnect();
    });
    observer.observe(document.getElementById('root') ?? document.body, { childList: true, subtree: true });
    window.addEventListener('pagehide', () => observer.disconnect(), { once: true });
  }
}
