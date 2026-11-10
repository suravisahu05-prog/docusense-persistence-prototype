import React, { useEffect, useRef, useState } from 'react';
import anime from 'animejs';
import Navbar from './components/Navbar.jsx';
import UploadZone from './components/UploadZone.jsx';
import Dashboard from './components/Dashboard.jsx';
import Loader from './components/Loader.jsx';
import { useReveal, shake } from './anim.js';

export default function App() {
  const [view, setView] = useState('upload');      // 'upload' | 'results'
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState(null);
  const [fileErrors, setFileErrors] = useState([]);
  const [error, setError] = useState('');
  const mainRef = useRef(null);

  /* SECTION: animated blob background */
  useEffect(() => {
    const a = anime({ targets: '.blob', translateX: anime.stagger([-80, 80]), translateY: anime.stagger([-60, 60]),
      duration: 8000, direction: 'alternate', easing: 'easeInOutSine', loop: true });
    return () => a.pause();
  }, []);

  /* SECTION: view transition fade + scroll reveal */
  useEffect(() => { anime({ targets: mainRef.current, opacity: [0, 1], duration: 300, easing: 'linear' }); }, [view]);
  useReveal(view + (data ? data.scan_id : ''));

  /* SECTION: upload + scan */
  async function scan(files) {
    setBusy(true); setError(''); setFileErrors([]);
    const fd = new FormData();
    files.forEach((f) => fd.append('files', f));
    try {
      const res = await fetch('/api/v1/upload-and-scan', { method: 'POST', body: fd });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const d = body.detail;
        setFileErrors(d?.file_errors || []);
        throw new Error(typeof d === 'string' ? d : d?.message || body.message || `Request failed (${res.status})`);
      }
      setFileErrors(body.errors || []);
      setData(body);
      if (body.documents_failed > 0 && body.documents_parsed === 0) return;
      setView('results');
    } catch (e) {
      setError(e.message || 'Network error');
      setTimeout(() => shake('.error'), 30);
    } finally { setBusy(false); }
  }

  /* SECTION: refresh dashboard (merge so summary/documents survive) */
  async function refresh() {
    if (!data?.scan_id) return;
    try {
      const res = await fetch(`/api/v1/scans/${data.scan_id}/dashboard`);
      if (!res.ok) throw new Error(`Refresh failed (${res.status})`);
      const d = await res.json();
      setData((prev) => ({ ...prev, findings: d.findings ?? prev.findings, general_analysis: d.general_analysis ?? prev.general_analysis }));
    } catch (e) { setError(e.message); setTimeout(() => shake('.error'), 30); }
  }

  const mode = /claude/i.test(data?.general_analysis?.extractor || '') ? 'Claude' : 'DEMO';

  return (
    <>
      <div className="bg" aria-hidden="true">
        <div className="blob b1" /><div className="blob b2" /><div className="blob b3" />
      </div>
      <Navbar mode={mode} view={view} hasResults={!!data} onNav={setView} />
      <main ref={mainRef} className="main">
        {view === 'upload' && (
          <>
            <section className="hero reveal">
              <h1>Find the facts your documents <span className="grad">disagree on</span></h1>
              <p>Upload policies, specs and manuals. DocuSense extracts structured facts and flags conflicts with evidence.</p>
            </section>
            <div className="reveal">
              <UploadZone busy={busy} onScan={scan} fileErrors={fileErrors} />
            </div>
            {error && <div className="error glass" role="alert">{error}</div>}
          </>
        )}
        {view === 'results' && data && (
          <Dashboard data={data} onRefresh={refresh} onNew={() => setView('upload')} error={error} />
        )}
      </main>
      {busy && <Loader label="Scanning…" overlay />}
    </>
  );
}
