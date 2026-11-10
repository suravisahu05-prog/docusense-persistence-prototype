import React, { useRef, useState } from 'react';
import anime from 'animejs';

const COLORS = { direct_conflict: 'var(--danger)', operational: 'var(--warn)', general: 'var(--accent)' };
const LABELS = { direct_conflict: 'Direct conflict', operational: 'Operational risk', general: 'Contradiction' };

export default function ConflictCard({ item, scanId }) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState(item.reviewStatus || 'open');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');
  const body = useRef(null), card = useRef(null);

  /* SECTION: evidence accordion (height tween 0 -> auto) */
  function toggle() {
    const el = body.current;
    if (!open) {
      anime({ targets: el, height: [0, el.scrollHeight], opacity: [0, 1], duration: 300, easing: 'easeOutQuad',
        complete: () => { el.style.height = 'auto'; } });
    } else {
      anime({ targets: el, height: [el.scrollHeight, 0], opacity: [1, 0], duration: 250, easing: 'easeInQuad' });
    }
    setOpen(!open);
  }

  /* SECTION: Mark Resolved / Ignore -> saved in SQLite + audit log via the API */
  async function change(action) {
    setSaving(true); setErr('');
    try {
      const res = await fetch(`/api/v1/scans/${scanId}/findings/${encodeURIComponent(item.id)}/status`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, actor: 'dashboard-user' }),
      });
      if (!res.ok) throw new Error(`Could not save (${res.status})`);
      const out = await res.json();
      setStatus(out.status);
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  }

  /* SECTION: hover micro-interaction */
  const hover = (on) => {
    anime({ targets: card.current, borderLeftWidth: on ? 6 : 4, duration: 150, easing: 'easeOutQuad' });
    card.current.style.filter = `brightness(${on ? 1.05 : 1})`;
  };

  return (
    <article ref={card} className={`conflict-card glass ${status !== 'open' ? 'reviewed' : ''}`}
      style={{ borderLeftColor: COLORS[item.kind], borderLeftWidth: 4 }}
      onMouseEnter={() => hover(true)} onMouseLeave={() => hover(false)}>
      <div className="cc-head">
        <span className={`pill sev ${item.severity.toLowerCase()}`}>{item.severity}</span>
        <span className="pill kind">{LABELS[item.kind]}</span>
        {item.confidence != null && <span className="pill conf">{item.confidence}% conf.</span>}
        <span className="mono muted id">{item.id}</span>
      </div>
      <h4 className="attr">{item.attribute}</h4>
      <div className="docs">
        {item.docs.map((d, i) => <span key={i} className="doc-pill" title={d}>📄 {d}</span>)}
      </div>
      <p className="muted small">{item.explanation}</p>
      <button className="link-btn" onClick={toggle} aria-expanded={open}>{open ? '▾' : '▸'} Evidence</button>
      <div ref={body} className="evidence" style={{ height: 0, opacity: 0, overflow: 'hidden' }}>
        {item.evidence.map((e, i) => (
          <blockquote key={i}><span className="mono muted">{item.docs[i] || `Source ${i + 1}`}</span>{e}</blockquote>
        ))}
      </div>
      <div className="review-actions">
        {status === 'open' ? (
          <>
            <button className="review-btn" disabled={saving} onClick={() => change('resolve')}>Mark Resolved</button>
            <button className="review-btn" disabled={saving} onClick={() => change('ignore')}>Ignore</button>
          </>
        ) : (
          <>
            <span className={`review-btn on`}>{status === 'resolved' ? '✓ Resolved' : 'Ignored'}</span>
            <button className="review-btn" disabled={saving} onClick={() => change('reopen')}>Reopen</button>
          </>
        )}
        {err && <span className="small" style={{ color: 'var(--danger)' }}>{err}</span>}
      </div>
    </article>
  );
}
