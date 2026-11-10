import React, { useEffect, useRef, useState } from 'react';
import anime from 'animejs';

export default function Navbar({ mode, view, hasResults, onNav }) {
  const bar = useRef(null), menu = useRef(null);
  const [open, setOpen] = useState(false);
  const shrunk = useRef(false);

  /* SECTION: shrink on scroll */
  useEffect(() => {
    const onScroll = () => {
      const s = window.scrollY > 60;
      if (s === shrunk.current) return;
      shrunk.current = s;
      anime({ targets: bar.current, paddingTop: s ? '0.4rem' : '0.75rem', paddingBottom: s ? '0.4rem' : '0.75rem',
        duration: 250, easing: 'easeOutQuad' });
      bar.current.style.backdropFilter = `blur(${s ? 26 : 18}px) saturate(180%)`;
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  /* SECTION: mobile slide-down */
  useEffect(() => {
    if (!menu.current) return;
    anime({ targets: menu.current, translateY: open ? [-12, 0] : 0, opacity: open ? [0, 1] : 1, duration: 250, easing: 'easeOutQuad' });
  }, [open]);

  const go = (v) => { onNav(v); setOpen(false); };
  const links = (
    <>
      <button className={`nav-link ${view === 'upload' ? 'on' : ''}`} onClick={() => go('upload')}>Upload</button>
      <button className={`nav-link ${view === 'results' ? 'on' : ''}`} disabled={!hasResults} onClick={() => go('results')}>Results</button>
    </>
  );

  return (
    <header ref={bar} className="navbar glass">
      <div className="nav-inner">
        <div className="logo"><span className="logo-mark">◈</span><span className="wordmark">DocuSense AI</span></div>
        <nav className="nav-links desktop">{links}</nav>
        <span className={`pill mode ${mode === 'Claude' ? 'claude' : 'demo'}`}>{mode}</span>
        <button className="burger" aria-label="Menu" onClick={() => setOpen((o) => !o)}>{open ? '✕' : '☰'}</button>
      </div>
      {open && <nav ref={menu} className="nav-links mobile">{links}</nav>}
    </header>
  );
}
