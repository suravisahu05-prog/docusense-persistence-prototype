import React, { useEffect, useRef } from 'react';
import anime from 'animejs';

/* SVG ring spinner: strokeDashoffset loop + rotation */
export default function Loader({ label = 'Loading…', overlay = false, size = 56 }) {
  const ring = useRef(null);
  useEffect(() => {
    const a = anime({ targets: ring.current, strokeDashoffset: [anime.setDashoffset, 0], duration: 1400,
      easing: 'easeInOutSine', loop: true, direction: 'alternate' });
    const r = anime({ targets: ring.current.parentNode, rotate: 360, duration: 1800, easing: 'linear', loop: true });
    return () => { a.pause(); r.pause(); };
  }, []);
  const body = (
    <div className="loader">
      <svg width={size} height={size} viewBox="0 0 50 50">
        <circle cx="25" cy="25" r="20" fill="none" stroke="rgba(255,255,255,.12)" strokeWidth="4" />
        <circle ref={ring} cx="25" cy="25" r="20" fill="none" stroke="var(--accent)" strokeWidth="4" strokeLinecap="round" />
      </svg>
      <span>{label}</span>
    </div>
  );
  return overlay ? <div className="overlay">{body}</div> : body;
}
