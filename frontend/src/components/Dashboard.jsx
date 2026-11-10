import React, { useEffect, useMemo, useRef, useState } from 'react';
import anime from 'animejs';
import ConflictCard from './ConflictCard.jsx';
import { ripple } from '../anim.js';

const FILTERS = [['all', 'All'], ['direct_conflict', 'Direct Conflicts'], ['operational', 'Operational Risks']];
const sevMap = { high: 'High', medium: 'Medium', low: 'Low' };
const ev = (e) => (typeof e === 'string' ? e : e?.quote || e?.text || e?.evidence || JSON.stringify(e));

/* SECTION: animated stat card */
function Stat({ icon, label, value }) {
  const num = useRef(null), card = useRef(null);
  useEffect(() => {
    const o = { v: 0 };
    anime({ targets: o, v: value, round: 1, duration: 1000, easing: 'easeOutExpo', update: () => { if (num.current) num.current.textContent = o.v; } });
  }, [value]);
  const hov = (on) => anime({ targets: card.current, translateY: on ? -4 : 0,
    boxShadow: on ? '0 16px 40px rgba(108,99,255,.35)' : '0 8px 32px rgba(0,0,0,.35)', duration: 250, easing: 'easeOutQuad' });
  return (
    <div ref={card} className="stat glass" onMouseEnter={() => hov(true)} onMouseLeave={() => hov(false)}>
      <span className="stat-icon">{icon}</span>
      <span ref={num} className="stat-num">0</span>
      <span className="muted small">{label}</span>
    </div>
  );
}

/* SECTION: consistency ring */
function Ring({ score }) {
  const arc = useRef(null), txt = useRef(null);
  useEffect(() => {
    const C = 2 * Math.PI * 52, o = { v: 0 };
    arc.current.style.strokeDasharray = C;
    anime({ targets: o, v: score, round: 1, duration: 1200, easing: 'easeOutElastic(1,.6)', update: () => {
      arc.current.style.strokeDashoffset = C * (1 - o.v / 100); txt.current.textContent = `${o.v}%`; } });
  }, [score]);
  const col = score >= 80 ? 'var(--ok)' : score >= 50 ? 'var(--warn)' : 'var(--danger)';
  return (
    <div className="score glass">
      <svg width="132" height="132" viewBox="0 0 132 132" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="66" cy="66" r="52" fill="none" stroke="rgba(255,255,255,.1)" strokeWidth="10" />
        <circle ref={arc} cx="66" cy="66" r="52" fill="none" stroke={col} strokeWidth="10" strokeLinecap="round" />
      </svg>
      <div className="score-txt"><span ref={txt} className="stat-num">0%</span><span className="muted small">Consistency</span></div>
    </div>
  );
}

export default function Dashboard({ data, onRefresh, onNew, error }) {
  const [filter, setFilter] = useState('all');
  const pills = useRef({});

  /* SECTION: normalise API payloads into one card shape */
  const technical = useMemo(() => (data.findings || []).map((f) => ({
    id: f.finding_id, reviewStatus: f.review_status || 'open', kind: f.type === 'direct_conflict' ? 'direct_conflict' : 'operational',
    severity: sevMap[f.severity] || f.severity, attribute: f.attribute.replace(/_/g, ' '),
    docs: f.documents || [], evidence: (f.evidence || []).map(ev), explanation: f.explanation, confidence: null,
  })), [data.findings]);

  const general = useMemo(() => (data.general_analysis?.contradictions || []).map((c) => ({
    id: `G-${c.id ?? ''}`, reviewStatus: c.review_status || 'open', kind: 'general', severity: c.severity, attribute: c.topic, confidence: c.confidence,
    docs: [c.source_a?.doc, c.source_b?.doc].filter(Boolean),
    evidence: [c.source_a, c.source_b].filter(Boolean).map((s) => `${s.quote || s.value} (section ${s.section || '-'}, value: ${s.value})`),
    explanation: `${c.status || 'NEEDS HUMAN REVIEW'}${c.scope ? ` · scope: ${c.scope}` : ''}${c.effective ? ` · effective ${c.effective}` : ''}`,
  })), [data.general_analysis]);

  const shown = filter === 'all' ? technical : technical.filter((f) => f.kind === filter);
  const s = data.summary || {};
  const docs = s.documents ?? data.documents_parsed ?? 0;
  const direct = s.direct_conflicts ?? technical.filter((t) => t.kind === 'direct_conflict').length;
  const risks = s.operational_risks ?? technical.filter((t) => t.kind === 'operational').length;
  const total = technical.length + general.length;
  const score = data.general_analysis?.consistency_score != null && !technical.length
    ? data.general_analysis.consistency_score
    : Math.max(0, Math.round(100 - (100 * total) / Math.max(docs, 1)));

  /* SECTION: staggered card entrance on filter/data change */
  useEffect(() => {
    anime({ targets: '.conflict-card', translateX: [-30, 0], opacity: [0, 1], delay: anime.stagger(80), duration: 500, easing: 'easeOutQuad' });
  }, [filter, technical, general]);

  /* SECTION: empty-state float loop */
  useEffect(() => {
    const a = anime({ targets: '.float-doc', translateY: [-8, 8], duration: 1800, direction: 'alternate', loop: true, easing: 'easeInOutSine' });
    return () => a.pause();
  }, [shown.length]);

  /* SECTION: filter pill toggle animation */
  function pick(k) {
    setFilter(k);
    anime({ targets: pills.current[k], scale: [0.95, 1], backgroundColor: ['rgba(255,255,255,.08)', '#6c63ff'], duration: 200, easing: 'easeOutQuad' });
  }

  return (
    <div className="dash">
      <div className="dash-top reveal">
        <h2>Scan results <span className="mono muted small">{data.scan_id?.slice(0, 8)}</span></h2>
        <div className="row">
          <button className="ghost" onClick={(e) => { ripple(e); onRefresh(); }}>↻ Refresh</button>
          <button className="ghost" onClick={(e) => { ripple(e); onNew(); }}>+ New scan</button>
        </div>
      </div>
      {error && <div className="error glass">{error}</div>}
      {data.documents_failed > 0 && <div className="error glass">{data.documents_failed} document(s) failed to parse: {(data.errors || []).map((e) => `${e.filename} (${e.message})`).join('; ')}</div>}

      <div className="stats reveal">
        <Stat icon="📄" label="Documents" value={docs} />
        <Stat icon="🧩" label="Technical Statements" value={s.eav_statements ?? 0} />
        <Stat icon="⚠️" label="Direct Conflicts" value={direct} />
        <Stat icon="🛰️" label="Operational Risks" value={risks} />
      </div>
      <div className="reveal"><Ring score={score} /></div>

      {general.length > 0 && (
        <section className="reveal">
          <h3>General Analysis</h3>
          <div className="cards">{general.map((c) => <ConflictCard key={c.id} item={c} scanId={data.scan_id} />)}</div>
        </section>
      )}

      <section className="reveal">
        <h3>Technical Findings</h3>
        <div className="filters" role="tablist">
          {FILTERS.map(([k, l]) => (
            <button key={k} ref={(el) => (pills.current[k] = el)} role="tab" aria-selected={filter === k}
              className={`pill filter ${filter === k ? 'active' : 'glass'}`} onClick={() => pick(k)}>{l}</button>
          ))}
        </div>
        {shown.length ? (
          <div className="cards">{shown.map((f) => <ConflictCard key={f.id} item={f} scanId={data.scan_id} />)}</div>
        ) : (
          <div className="empty">
            <svg className="float-doc" width="72" height="72" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.5" strokeLinejoin="round">
              <path d="M6 2h8l5 5v15H6z" /><path d="M14 2v5h5M9 13h7M9 17h5" />
            </svg>
            <p className="muted">No findings here. Your documents look consistent.</p>
          </div>
        )}
      </section>
    </div>
  );
}
