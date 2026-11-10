import React, { useEffect, useRef, useState } from 'react';
import anime from 'animejs';
import Loader from './Loader.jsx';
import { ripple, shake, fmtSize } from '../anim.js';

const OK = ['.pdf', '.docx', '.txt', '.md'];
const MAX = 25 * 1024 * 1024;

export default function UploadZone({ busy, onScan, fileErrors }) {
  const [files, setFiles] = useState([]);
  const [drag, setDrag] = useState(false);
  const [msg, setMsg] = useState('');
  const input = useRef(null);

  /* SECTION: pulsing ring */
  useEffect(() => {
    const a = anime({ targets: '.upload-ring', scale: [1, 1.08], opacity: [0.6, 1], duration: 1200,
      direction: 'alternate', loop: true, easing: 'easeInOutQuad' });
    return () => a.pause();
  }, []);

  /* SECTION: add files with type + size guards */
  function add(list) {
    const bad = [], good = [];
    [...list].forEach((f) => {
      const ext = '.' + f.name.split('.').pop().toLowerCase();
      if (!OK.includes(ext)) bad.push(`${f.name}: unsupported type`);
      else if (f.size > MAX) bad.push(`${f.name}: exceeds 25 MB`);
      else if (!files.some((x) => x.name === f.name && x.size === f.size)) good.push(f);
    });
    setFiles((p) => [...p, ...good]);
    setMsg(bad.join(' · '));
    if (bad.length) setTimeout(() => shake('.upload-msg'), 20);
  }

  const errFor = (name) => fileErrors?.find((e) => e.filename === name)?.message;
  useEffect(() => { if (fileErrors?.length) shake('.chip.bad'); }, [fileErrors]);

  const hover = (e, on) => anime({ targets: e.currentTarget, scale: on ? 1.03 : 1, translateY: on ? -2 : 0, duration: 150, easing: 'easeOutQuad' });

  return (
    <div className={`upload glass ${drag ? 'drag' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); add(e.dataTransfer.files); }}>
      <svg className="dash-border" preserveAspectRatio="none"><rect x="1" y="1" width="calc(100% - 2px)" height="calc(100% - 2px)" rx="16" /></svg>
      <div className="drop" onClick={() => input.current.click()} role="button" tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && input.current.click()}>
        <div className="icon-wrap"><span className="upload-ring" /><span className="upload-icon">⇪</span></div>
        <h3>Drop documents here or click to browse</h3>
        <p className="muted">PDF · DOCX · TXT · MD — up to 25 MB each</p>
        <input ref={input} type="file" multiple hidden accept={OK.join(',')}
          onChange={(e) => { add(e.target.files); e.target.value = ''; }} />
      </div>
      {msg && <div className="upload-msg error-text">{msg}</div>}
      {files.length > 0 && (
        <div className="chips">
          {files.map((f) => {
            const err = errFor(f.name);
            return (
              <div key={f.name + f.size} className={`chip ${err ? 'bad' : ''}`}
                onMouseEnter={(e) => hover(e, true)} onMouseLeave={(e) => hover(e, false)}>
                <span className="chip-name">{f.name}</span><span className="muted mono">{fmtSize(f.size)}</span>
                <button aria-label={`Remove ${f.name}`} disabled={busy}
                  onClick={() => setFiles((p) => p.filter((x) => x !== f))}>✕</button>
                {err && <div className="chip-err">{err}</div>}
              </div>
            );
          })}
        </div>
      )}
      <div className="cta-row">
        {busy ? <Loader label="Scanning…" size={36} /> : (
          <button className="cta" disabled={!files.length}
            onClick={(e) => { ripple(e); onScan(files); }}>Analyze Documents</button>
        )}
      </div>
    </div>
  );
}
