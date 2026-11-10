/* SHARED ANIME.JS HELPERS */
import { useEffect } from 'react';
import anime from 'animejs';

/* Scroll reveal: observe each .reveal once, play translateY + opacity */
export function useReveal(dep) {
  useEffect(() => {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        anime({ targets: e.target, opacity: [0, 1], translateY: [40, 0], duration: 700, easing: 'easeOutExpo' });
      });
    }, { threshold: 0.1 });
    document.querySelectorAll('.reveal:not([data-seen])').forEach((el) => {
      el.dataset.seen = '1';
      io.observe(el);
    });
    return () => io.disconnect();
  }, [dep]);
}

/* Button ripple: animates CSS vars consumed by the ::after pseudo-element */
export function ripple(e) {
  const btn = e.currentTarget;
  if (btn.disabled) return;
  const r = btn.getBoundingClientRect();
  btn.style.setProperty('--rx', `${e.clientX - r.left}px`);
  btn.style.setProperty('--ry', `${e.clientY - r.top}px`);
  const s = { scale: 0, opacity: 1 };
  anime({
    targets: s, scale: 3, opacity: 0, duration: 150, easing: 'linear',
    update: () => { btn.style.setProperty('--rs', s.scale); btn.style.setProperty('--ro', s.opacity); },
  });
}

export const shake = (targets) =>
  anime({ targets, translateX: [-8, 8, -6, 6, -3, 3, 0], duration: 400, easing: 'easeInOutSine' });

export const fmtSize = (b) => (b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`);
