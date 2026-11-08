import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, ArrowDownToLine, ArrowRight, Check, ChevronLeft, ChevronRight, CircleHelp, Copy, Eye, Leaf, LogIn, LogOut, Plus, Radio, RefreshCw, Settings2, SlidersHorizontal, Thermometer, Trash2, X } from 'lucide-react';
import './style.css';

const number = (v) => new Intl.NumberFormat('pl-PL', { maximumFractionDigits: 2 }).format(v);
const time = (v, date = false) => new Date(v).toLocaleString('pl-PL', date ? { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' } : { hour: '2-digit', minute: '2-digit' });
const localInput = (d) => new Date(d - new Date(d).getTimezoneOffset() * 60000).toISOString().slice(0, 16);
const markers = ['circle', 'square', 'diamond', 'triangle'];
const markerName = { circle: 'koło', square: 'kwadrat', diamond: 'romb', triangle: 'trójkąt' };

async function api(path, { method = 'GET', body, token, signal } = {}) {
  const res = await fetch(`/api${path}`, { method, signal, headers: {
    Accept: 'application/json', ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }, ...(body !== undefined ? { body: JSON.stringify(body) } : {}) });
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) {
    const error = new Error(data.detail || data.title || 'Nie udało się wykonać operacji.');
    error.status = res.status;
    throw error;
  }
  return data;
}

function Shape({ kind = 'circle', x = 8, y = 8, size = 4, ...props }) {
  if (kind === 'square') return <rect x={x - size} y={y - size} width={size * 2} height={size * 2} {...props} />;
  if (kind === 'diamond') return <path d={`M${x} ${y - size * 1.3}l${size * 1.3} ${size * 1.3}l${-size * 1.3} ${size * 1.3}l${-size * 1.3} ${-size * 1.3}Z`} {...props} />;
  if (kind === 'triangle') return <path d={`M${x} ${y - size * 1.4}l${size * 1.3} ${size * 2.4}h${-size * 2.6}Z`} {...props} />;
  return <circle cx={x} cy={y} r={size} {...props} />;
}
function Swatch({ series, index = 0 }) {
  return <svg width="18" height="18" viewBox="0 0 16 16" aria-hidden="true"><Shape kind={series.icon || markers[index % 4]} fill={series.color} /></svg>;
}
function Alert({ children }) { return children ? <div className="alert" role="alert">{children}</div> : null; }
function Empty({ title, children }) { return <div className="empty"><Activity size={30} /><h3>{title}</h3><p>{children}</p></div>; }

function Modal({ title, children, onClose, wide = false }) {
  const ref = useRef(null);
  useEffect(() => { const el = ref.current; el.showModal(); return () => el.close(); }, []);
  return <dialog ref={ref} className={wide ? 'modal wide' : 'modal'} onCancel={(e) => { e.preventDefault(); onClose(); }} aria-labelledby="modal-title">
    <div className="modal-heading"><h2 id="modal-title">{title}</h2><button className="icon-btn" aria-label="Zamknij okno" onClick={onClose}><X size={20} /></button></div>
    {children}
  </dialog>;
}

function LoginForm({ onLogin, onClose }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault(); const f = new FormData(e.currentTarget); setBusy(true); setError('');
    try { const result = await api('/auth/login', { method: 'POST', body: Object.fromEntries(f) }); onLogin(result.accessToken, f.get('username')); }
    catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <Modal title="Witaj z powrotem" onClose={onClose}><p className="muted">Zaloguj się, aby zarządzać seriami i czujnikami.</p>
    <form onSubmit={submit} className="stack"><label>Login<input name="username" autoComplete="username" required maxLength={100} autoFocus /></label>
      <label>Hasło<input name="password" type="password" autoComplete="current-password" required maxLength={1024} /></label>
      <Alert>{error}</Alert><button className="btn primary" disabled={busy}>{busy ? 'Logowanie…' : 'Zaloguj się'}<ArrowRight size={17} /></button>
    </form></Modal>;
}

function Chart({ series, measurements, selected }) {
  const width = 1000, height = 300, pad = { l: 55, r: 20, t: 24, b: 42 };
  if (!measurements.length) return <Empty title="Tutaj pojawią się pomiary">Wybierz serie i zakres czasu lub prześlij dane z czujnika.</Empty>;
  const dates = measurements.map(m => Date.parse(m.timestamp));
  let x0 = Math.min(...dates), x1 = Math.max(...dates);
  if (x0 === x1) { x0 -= 60000; x1 += 60000; }
  const values = measurements.map(m => m.value);
  let y0 = Math.min(...values), y1 = Math.max(...values);
  const margin = Math.max((y1 - y0) * .2, 1); y0 -= margin; y1 += margin;
  const x = v => pad.l + (Date.parse(v) - x0) / (x1 - x0) * (width - pad.l - pad.r);
  const y = v => height - pad.b - (v - y0) / (y1 - y0) * (height - pad.t - pad.b);
  const active = measurements.find(m => m.id === selected);
  return <div className="chart-wrap"><svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-labelledby="chart-title chart-desc">
    <title id="chart-title">Pomiary w czasie — {series.map(s => s.name).join(', ')}</title>
    <desc id="chart-desc">{measurements.length} pomiarów. Pełne wartości i wybór punktów są dostępne w tabeli pod wykresem. Linie mają różne znaczniki i wzory.</desc>
    {Array.from({ length: 5 }, (_, i) => { const v = y0 + (y1 - y0) * i / 4; return <g key={i}><line x1={pad.l} x2={width - pad.r} y1={y(v)} y2={y(v)} className="grid-line" /><text x={pad.l - 12} y={y(v) + 4} textAnchor="end" className="axis-label">{number(v)}</text></g>; })}
    {Array.from({ length: 6 }, (_, i) => { const d = x0 + (x1 - x0) * i / 5; return <text key={i} x={x(new Date(d).toISOString())} y={height - 12} textAnchor={i === 0 ? 'start' : i === 5 ? 'end' : 'middle'} className="axis-label">{x1 - x0 > 86400000 ? new Date(d).toLocaleDateString('pl-PL', { day: 'numeric', month: 'short' }) : time(d)}</text>; })}
    {series.map((s, index) => {
      const points = measurements.filter(m => m.seriesId === s.id);
      if (!points.length) return null;
      const d = points.map((m, i) => `${i ? 'L' : 'M'}${x(m.timestamp)},${y(m.value)}`).join(' ');
      return <g key={s.id}><path d={d} fill="none" stroke={s.color} strokeWidth="2.5" strokeLinejoin="round" strokeDasharray={['', '7 4', '2 5', '9 3 2 3'][index % 4]} />
        {points.filter((_, i) => i % Math.max(1, Math.ceil(points.length / 70)) === 0).map(m => <Shape key={m.id} kind={s.icon || markers[index % 4]} x={x(m.timestamp)} y={y(m.value)} size={3.5} fill="white" stroke={s.color} strokeWidth="1.8" />)}</g>;
    })}
    {active && <g data-testid="selected-point"><line x1={x(active.timestamp)} x2={x(active.timestamp)} y1={pad.t} y2={height - pad.b} stroke="#173e35" strokeDasharray="3 4" /><circle cx={x(active.timestamp)} cy={y(active.value)} r="10" fill="#e1eb9b" stroke="#173e35" strokeWidth="3" /><circle cx={x(active.timestamp)} cy={y(active.value)} r="3" fill="#173e35" /></g>}
  </svg></div>;
}

function DataTable({ series, measurements, selected, onSelect }) {
  const [page, setPage] = useState(0);
  useEffect(() => setPage(0), [measurements]);
  const rows = useMemo(() => {
    const result = new Map();
    for (const m of measurements) {
      if (!result.has(m.timestamp)) result.set(m.timestamp, new Map());
      const row = result.get(m.timestamp);
      if (!row.has(m.seriesId)) row.set(m.seriesId, []);
      row.get(m.seriesId).push(m);
    }
    return [...result].reverse();
  }, [measurements]);
  const pages = Math.max(1, Math.ceil(rows.length / 10));
  const renderRows = (items) => items.map(([stamp, values]) => <tr key={stamp} className={[...values.values()].flat().some(m => m.id === selected) ? 'selected-row' : ''}>
    <th scope="row"><span>{time(stamp)}</span><small>{new Date(stamp).toLocaleDateString('pl-PL', { day: 'numeric', month: 'short', year: 'numeric' })}</small></th>
    {series.map(s => <td key={s.id}>{values.has(s.id) ? values.get(s.id).map(m => <button key={m.id} className={`value-btn ${m.id === selected ? 'chosen' : ''}`} aria-pressed={m.id === selected} onClick={() => onSelect(m.id)} aria-label={`${s.name}, ${number(m.value)} ${s.unit || ''}, ${time(m.timestamp, true)}. Wyróżnij na wykresie.`}>{number(m.value)}<span className="value-unit">{s.unit || ''}</span>{m.id === selected && <Eye size={13} />}</button>) : <span className="muted" aria-label="Brak pomiaru">—</span>}</td>)}
  </tr>);
  return <section className="panel table-panel"><div className="section-heading"><div><span className="eyebrow">DANE ŹRÓDŁOWE</span><h2>Każdy pomiar ma znaczenie<span className="count-pill">{measurements.length}</span></h2></div><span className="table-hint no-print"><Eye size={15} />Kliknij wartość, aby wyróżnić punkt</span></div>
    {!rows.length ? <Empty title="Brak wyników w tym zakresie">Spróbuj poszerzyć przedział czasu.</Empty> : <>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Tabela pomiarów, przewijana poziomo"><table><caption className="sr-only">Pomiary według czasu. Każda seria jest osobną kolumną. Kilka wyników z tej samej chwili pozostaje widocznych.</caption>
        <thead><tr><th scope="col">Czas pomiaru</th>{series.map((s, i) => <th scope="col" key={s.id}><span className="inline"><Swatch series={s} index={i} />{s.name}</span></th>)}</tr></thead>
        <tbody className="screen-rows">{renderRows(rows.slice(page * 10, page * 10 + 10))}</tbody><tbody className="print-rows">{renderRows(rows)}</tbody>
      </table></div><div className="pagination no-print"><span>{page * 10 + 1}–{Math.min((page + 1) * 10, rows.length)} z {rows.length} znaczników czasu</span><div className="inline"><button className="icon-btn" aria-label="Poprzednia strona" disabled={page === 0} onClick={() => setPage(page - 1)}><ChevronLeft size={18} /></button><span>{page + 1} / {pages}</span><button className="icon-btn" aria-label="Następna strona" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}><ChevronRight size={18} /></button></div></div>
    </>}
  </section>;
}

function SeriesEditor({ current, token, onClose, onSaved, onError }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault(); const f = new FormData(e.currentTarget);
    const body = { name: f.get('name').trim(), minValue: Number(f.get('minValue')), maxValue: Number(f.get('maxValue')), color: f.get('color'), icon: f.get('icon'), unit: f.get('unit') || null };
    if (!body.name || body.minValue >= body.maxValue) { setError('Podaj nazwę i zakres, w którym minimum jest mniejsze od maksimum.'); return; }
    setBusy(true); setError('');
    try { await api(`/series${current ? `/${current.id}` : ''}`, { method: current ? 'PUT' : 'POST', body, token }); onSaved('Seria została zapisana.'); }
    catch (err) { setError(err.message); onError(err); } finally { setBusy(false); }
  }
  return <Modal title={current ? 'Edytuj serię' : 'Nowa seria pomiarowa'} onClose={onClose}><form className="stack" onSubmit={submit}>
    <label>Nazwa serii<input name="name" defaultValue={current?.name || ''} maxLength={100} required autoFocus placeholder="np. Szklarnia północna" /></label>
    <div className="form-grid"><label>Minimum<input name="minValue" type="number" step="any" defaultValue={current?.minValue ?? -20} required /></label><label>Maksimum<input name="maxValue" type="number" step="any" defaultValue={current?.maxValue ?? 50} required /></label></div>
    <div className="form-grid"><label>Jednostka<input name="unit" maxLength={20} defaultValue={current?.unit ?? '°C'} placeholder="np. °C" /></label><label>Kolor<input name="color" type="color" defaultValue={current?.color || '#28715e'} required /></label></div>
    <label>Znacznik punktu<select name="icon" defaultValue={current?.icon || 'circle'}>{markers.map(m => <option key={m} value={m}>{markerName[m]}</option>)}</select></label>
    <p className="form-note">Zmiana zakresu nie może wykluczyć już zapisanych pomiarów.</p><Alert>{error}</Alert><button className="btn primary" disabled={busy}>{busy ? 'Zapisywanie…' : 'Zapisz serię'}<Check size={17} /></button>
  </form></Modal>;
}

function SensorEditor({ series, token, onClose, onSaved, onError }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const [created, setCreated] = useState(null); const [copied, setCopied] = useState(false);
  async function submit(e) {
    e.preventDefault(); const f = new FormData(e.currentTarget); setBusy(true); setError('');
    if (!f.get('name').trim()) { setError('Podaj nazwę czujnika.'); setBusy(false); return; }
    try { const sensor = await api('/sensors', { method: 'POST', token, body: { name: f.get('name').trim(), seriesId: f.get('seriesId') } }); setCreated(sensor); onSaved(); }
    catch (err) { setError(err.message); onError(err); } finally { setBusy(false); }
  }
  return <Modal title={created ? 'Czujnik jest gotowy' : 'Zarejestruj czujnik'} onClose={onClose}>{created ? <div className="stack"><div className="key-success"><Check size={24} /><strong>{created.name}</strong></div><p>Skopiuj klucz do generatora. Po zamknięciu tego okna nie będzie można go ponownie odczytać.</p>
    <label>Klucz API<input className="secret-key" readOnly value={created.apiKey} onFocus={e => e.target.select()} /></label>
    <button className="btn secondary" onClick={async () => { try { await navigator.clipboard.writeText(created.apiKey); setCopied(true); } catch { setError('Zaznacz i skopiuj klucz ręcznie.'); } }}><Copy size={16} />{copied ? 'Skopiowano' : 'Kopiuj klucz'}</button><Alert>{error}</Alert>
    <p className="form-note">W generatorze ustaw zmienną SPLOT_API_KEY. Adres API: {window.location.origin}</p><button className="btn primary" onClick={onClose}>Klucz zapisany, zamknij</button>
  </div> : <form className="stack" onSubmit={submit}><label>Nazwa czujnika<input name="name" maxLength={100} required autoFocus placeholder="np. Termometr 01" /></label>
    <label>Seria pomiarowa<select name="seriesId" required defaultValue={series[0]?.id || ''}>{series.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label><p className="form-note">Czujnik będzie mógł przesyłać pomiary tylko do wybranej serii.</p><Alert>{error}</Alert><button className="btn primary" disabled={busy || !series.length}>{busy ? 'Rejestrowanie…' : 'Zarejestruj czujnik'}<Plus size={17} /></button></form>}</Modal>;
}

function PasswordEditor({ token, onClose, onSaved, onError }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault(); const f = new FormData(e.currentTarget);
    if (f.get('newPassword') !== f.get('confirm')) { setError('Nowe hasła muszą być identyczne.'); return; }
    setBusy(true); setError('');
    try { await api('/auth/password', { method: 'PUT', token, body: { currentPassword: f.get('currentPassword'), newPassword: f.get('newPassword') } }); onSaved(); }
    catch (err) { setError(err.message); onError(err); } finally { setBusy(false); }
  }
  return <Modal title="Zmień hasło" onClose={onClose}><form className="stack" onSubmit={submit}><label>Bieżące hasło<input name="currentPassword" type="password" autoComplete="current-password" required autoFocus /></label><label>Nowe hasło<input name="newPassword" type="password" minLength={8} maxLength={1024} autoComplete="new-password" required /></label><label>Powtórz nowe hasło<input name="confirm" type="password" minLength={8} maxLength={1024} autoComplete="new-password" required /></label><p className="form-note">Co najmniej 8 znaków. Zmiana hasła zakończy wszystkie sesje administratora.</p><Alert>{error}</Alert><button className="btn primary" disabled={busy}>{busy ? 'Zapisywanie…' : 'Zmień hasło'}</button></form></Modal>;
}

function DeleteDialog({ target, token, onClose, onSaved, onError }) {
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function remove() {
    setBusy(true); try { await api(`/${target.type}/${target.item.id}`, { method: 'DELETE', token }); onSaved(target.type === 'series' ? 'Seria została usunięta.' : 'Czujnik został wyrejestrowany.'); }
    catch (err) { setError(err.message); onError(err); } finally { setBusy(false); }
  }
  return <Modal title={target.type === 'series' ? 'Usunąć serię?' : 'Wyrejestrować czujnik?'} onClose={onClose}><p><strong>{target.item.name}</strong></p><p>{target.type === 'series' ? 'Usunięte zostaną także wszystkie pomiary i czujniki tej serii. Tej operacji nie można cofnąć.' : 'Klucz tego czujnika natychmiast przestanie działać. Zebrane pomiary pozostaną dostępne.'}</p><Alert>{error}</Alert><div className="modal-actions"><button className="btn secondary" onClick={onClose}>Anuluj</button><button className="btn danger" disabled={busy} onClick={remove}>{busy ? 'Usuwanie…' : target.type === 'series' ? 'Usuń serię i pomiary' : 'Wyrejestruj'}</button></div></Modal>;
}

function App() {
  const [view, setView] = useState('overview'); const [series, setSeries] = useState([]); const [measurements, setMeasurements] = useState([]); const [sensors, setSensors] = useState([]);
  const [chosen, setChosen] = useState(null); const [selected, setSelected] = useState(null);
  const [range, setRange] = useState({ from: localInput(Date.now() - 86400000), to: '' }); const [draft, setDraft] = useState(range); const [preset, setPreset] = useState('24h');
  const [token, setToken] = useState(null); const [username, setUsername] = useState(''); const [modal, setModal] = useState(null);
  const [revision, setRevision] = useState(0); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [notice, setNotice] = useState(''); const [live, setLive] = useState('connecting');
  const [sensorError, setSensorError] = useState(''); const [sensorLoading, setSensorLoading] = useState(false);
  const refresh = useCallback(() => setRevision(r => r + 1), []);
  const authError = useCallback(err => { if (err.status === 401) { setToken(null); setModal(null); setView('overview'); setNotice('Sesja wygasła. Zaloguj się ponownie.'); } }, []);
  const query = useMemo(() => { const q = new URLSearchParams({ limit: '10000', sort: '-timestamp' }); if (chosen?.length) q.set('series', chosen.join(',')); if (range.from) q.set('from', new Date(range.from).toISOString()); if (range.to) q.set('to', new Date(range.to).toISOString()); return q.toString(); }, [chosen, range]);
  useEffect(() => {
    const controller = new AbortController(); setLoading(true);
    Promise.all([api('/series', { signal: controller.signal }), chosen?.length === 0 ? Promise.resolve([]) : api(`/measurements?${query}`, { signal: controller.signal })])
      .then(([s, m]) => { setSeries(s); setMeasurements(m.reverse()); setError(''); })
      .catch(err => { if (err.name !== 'AbortError') setError('Nie udało się odczytać danych. Sprawdź połączenie i spróbuj ponownie.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query, revision]);
  useEffect(() => {
    if (!token) { setSensors([]); return; }
    const controller = new AbortController(); setSensorLoading(true);
    api('/sensors', { token, signal: controller.signal }).then(s => { setSensors(s); setSensorError(''); }).catch(err => { if (err.name !== 'AbortError') { setSensorError(err.message); authError(err); } }).finally(() => { if (!controller.signal.aborted) setSensorLoading(false); });
    return () => controller.abort();
  }, [token, revision, authError]);
  useEffect(() => {
    const stream = new EventSource('/api/events'); let timeout;
    stream.onopen = () => setLive('connected');
    stream.addEventListener('update', () => { clearTimeout(timeout); timeout = setTimeout(refresh, 200); });
    stream.onerror = () => setLive('reconnecting');
    return () => { clearTimeout(timeout); stream.close(); };
  }, [refresh]);
  const visible = series.filter(s => chosen === null || chosen.includes(s.id));
  const activePoint = measurements.find(m => m.id === selected);
  const units = [...new Set(visible.map(s => s.unit || 'wartość'))];
  const close = () => setModal(null);
  const saved = (message) => { close(); refresh(); setNotice(message); };
  function setPeriod(p) { const next = { from: p === 'all' ? '' : localInput(Date.now() - (p === '7d' ? 7 : 1) * 86400000), to: '' }; setPreset(p); setRange(next); setDraft(next); setSelected(null); }
  function applyRange(e) { e.preventDefault(); if (draft.from && draft.to && draft.from > draft.to) { setError('Początek zakresu nie może być późniejszy niż koniec.'); return; } setError(''); setRange(draft); setPreset('custom'); setSelected(null); }
  async function logout() { try { await api('/auth/logout', { method: 'POST', token }); setToken(null); setView('overview'); setNotice('Wylogowano.'); } catch (err) { authError(err); setNotice(err.message); } }
  return <>
    <a className="skip-link" href="#main">Przejdź do treści</a>
    <header className="topbar no-print"><div className="topbar-inner"><a className="brand" href="#" onClick={e => { e.preventDefault(); setView('overview'); }} aria-label="Splot — strona główna"><img src="/favicon.svg" width="38" height="38" alt="" /><span>splot<span className="brand-dot">.</span></span><span className="brand-caption">OBSERWATORIUM<br />MIKROKLIMATU</span></a>
      <nav aria-label="Nawigacja główna">{[['overview', 'Pulpit', Activity], ['series', 'Serie', SlidersHorizontal], ['sensors', 'Czujniki', Radio]].map(([id, label, Icon]) => <button key={id} className={`nav-btn ${view === id ? 'active' : ''}`} aria-current={view === id ? 'page' : undefined} onClick={() => { if (id === 'sensors' && !token) setModal({ type: 'login', next: id }); else setView(id); }}><Icon size={17} />{label}</button>)}</nav>
      <div className="account">{token ? <><button className="icon-btn" onClick={() => setModal({ type: 'password' })} aria-label="Zmień hasło"><Settings2 size={18} /></button><span className="account-name">{username}</span><button className="btn text-btn" onClick={logout}><LogOut size={16} /><span>Wyloguj</span></button></> : <button className="btn login-btn" onClick={() => setModal({ type: 'login' })}><LogIn size={16} />Administrator</button>}</div>
    </div></header>
    <main id="main" className="main-shell">
      <div className="page-heading"><div><div className="eyebrow"><span className="tiny-line" />TWOJE MAŁE OBSERWATORIUM</div><h1>{view === 'overview' ? <>Zobacz, jak zmienia się <em>klimat.</em></> : view === 'series' ? <>Każde miejsce. <em>Osobna historia.</em></> : <>Małe czujniki. <em>Wielki obraz.</em></>}</h1><p>{view === 'overview' ? 'Temperatura w czasie. Zebrana w jednym miejscu.' : view === 'series' ? 'Porządkuj pomiary, nadając im nazwę, zakres i własny charakter.' : 'Zarządzaj źródłami danych swojego obserwatorium.'}</p></div>
        <div className="heading-actions no-print">{view === 'overview' ? <button className="btn secondary" onClick={() => window.print()}><ArrowDownToLine size={17} />Drukuj raport</button> : token && <button className="btn primary" disabled={view === 'sensors' && !series.length} onClick={() => setModal({ type: view === 'series' ? 'series' : 'sensor' })}><Plus size={18} />{view === 'series' ? 'Dodaj serię' : 'Dodaj czujnik'}</button>}</div>
      </div>
      <div className="notice no-print" role="status" aria-live="polite">{notice && <><Check size={16} /><span>{notice}</span><button className="icon-btn" aria-label="Ukryj komunikat" onClick={() => setNotice('')}><X size={16} /></button></>}</div>
      <Alert>{error}</Alert>
      {error && <button className="btn secondary no-print" onClick={refresh}><RefreshCw size={16} />Spróbuj ponownie</button>}
      {view === 'overview' && <>
        <section className="series-summary" aria-label="Podsumowanie wybranych serii">{visible.length ? visible.map((s, i) => {
          const points = measurements.filter(m => m.seriesId === s.id), last = points.at(-1); const delta = points.length > 1 ? last.value - points[0].value : null;
          return <article className={`metric-card tone-${i % 3}`} key={s.id}><div className="metric-top"><span className="inline"><Swatch series={s} index={i} />{s.name}</span><Thermometer size={19} /></div><div className="metric-value">{last ? number(last.value) : '—'}<span>{s.unit || ''}</span><svg className="spark" viewBox="0 0 100 32" aria-hidden="true">{points.length > 1 && <polyline fill="none" stroke={s.color} strokeWidth="2" points={points.filter((_, j) => j % Math.max(1, Math.ceil(points.length / 40)) === 0).map((m, j, arr) => `${j / Math.max(arr.length - 1, 1) * 100},${29 - (m.value - Math.min(...points.map(p => p.value))) / Math.max(1, Math.max(...points.map(p => p.value)) - Math.min(...points.map(p => p.value))) * 25}`).join(' ')} />}</svg></div><div className="metric-bottom"><span>{delta !== null ? `${delta >= 0 ? '+' : ''}${number(delta)} ${s.unit || ''} w zakresie` : 'Oczekiwanie na dane'}</span><span>{points.length} pomiarów</span></div></article>;
        }) : <div className="summary-empty">{series.length ? 'Zaznacz przynajmniej jedną serię w filtrach.' : 'Obserwatorium czeka na pierwsze serie i pomiary.'}</div>}</section>
        <section className="panel chart-panel"><div className="section-heading"><div><span className="eyebrow">PERSPEKTYWA CZASU</span><h2>Rytm twojego otoczenia</h2></div><span className={`live-pill no-print ${live === 'connected' ? 'online' : ''}`}><span className="status-dot" />{live === 'connected' ? 'Na żywo' : live === 'connecting' ? 'Łączenie…' : 'Wznawianie połączenia…'}</span></div>
          <div className="filter-bar no-print"><div className="periods" aria-label="Szybki zakres czasu">{[['24h', '24 godziny'], ['7d', '7 dni'], ['all', 'Wszystkie']].map(([key, label]) => <button key={key} aria-pressed={preset === key} className={preset === key ? 'selected' : ''} onClick={() => setPeriod(key)}>{label}</button>)}</div><form className="date-filter" onSubmit={applyRange}><label>Od<input aria-label="Początek zakresu" type="datetime-local" value={draft.from} onChange={e => setDraft({ ...draft, from: e.target.value })} /></label><label>Do<input aria-label="Koniec zakresu" type="datetime-local" value={draft.to} onChange={e => setDraft({ ...draft, to: e.target.value })} /></label><button className="icon-btn apply-filter" aria-label="Zastosuj zakres czasu"><ArrowRight size={18} /></button></form></div>
          <div className="legend-row"><div className="legend-items">{series.map((s, i) => <label key={s.id} className="legend-item"><input type="checkbox" checked={chosen === null || chosen.includes(s.id)} onChange={e => { const ids = chosen ?? series.map(s => s.id); setChosen(e.target.checked ? [...ids, s.id] : ids.filter(id => id !== s.id)); setSelected(null); }} /><Swatch series={s} index={i} /><span>{s.name}</span></label>)}</div><span className="chart-unit">{units.length === 1 ? units[0] : 'Wartości / różne jednostki'}</span></div>
          <div className="loading-line" role="status">{loading ? 'Aktualizowanie pomiarów…' : ''}</div>
          <Chart series={visible} measurements={measurements} selected={selected} />
          <div className="chart-footer"><span className="inline"><CircleHelp size={15} />{activePoint ? `${series.find(s => s.id === activePoint.seriesId)?.name}: ${number(activePoint.value)} · ${time(activePoint.timestamp, true)}` : 'Za każdą linią stoi historia jednego miejsca.'}</span><span>{range.from ? time(new Date(range.from), true) : 'Początek obserwacji'} — {range.to ? time(new Date(range.to), true) : 'teraz'}</span></div>
          {measurements.length === 10000 && <p className="limit-note">Wyświetlono 10 000 najnowszych pomiarów w zakresie. Zawęź czas lub liczbę serii, aby zobaczyć pełne dane.</p>}
        </section>
        <DataTable series={visible} measurements={measurements} selected={selected} onSelect={setSelected} />
      </>}
      {view === 'series' && <section className="management-grid">{!series.length && <Empty title="Zacznij od pierwszej serii">Zaloguj się jako administrator i dodaj miejsce, które chcesz obserwować.</Empty>}{series.map((s, i) => <article className="panel series-detail" key={s.id}><div className="inline"><span className="series-symbol"><Swatch series={s} index={i} /></span><span className="eyebrow">SERIA {String(s.id).padStart(2, '0')}</span></div><h2>{s.name}</h2><p>Dopuszczalny zakres</p><div className="range-display">{number(s.minValue)}<span>—</span>{number(s.maxValue)}<small>{s.unit || ''}</small></div><p className="muted">Znacznik: {markerName[s.icon] || 'koło'} · Kolor: {s.color}</p>{token && <div className="card-actions"><button className="btn secondary" onClick={() => setModal({ type: 'series', current: s })}><Settings2 size={16} />Edytuj</button><button className="icon-btn delete-btn" aria-label={`Usuń serię ${s.name}`} onClick={() => setModal({ type: 'delete', target: { type: 'series', item: s } })}><Trash2 size={17} /></button></div>}</article>)}</section>}
      {view === 'sensors' && token && <section className="panel"><div className="section-heading"><div><span className="eyebrow">ŹRÓDŁA POMIARÓW</span><h2>Połączone czujniki<span className="count-pill">{sensors.length}</span></h2></div><Radio size={24} /></div><Alert>{sensorError}</Alert>{sensorLoading && <p role="status">Aktualizowanie czujników…</p>}
        {!sensors.length ? <Empty title="Podłącz pierwsze źródło danych">{series.length ? 'Zarejestruj czujnik i użyj jego klucza w generatorze.' : 'Najpierw utwórz serię pomiarową w zakładce Serie.'}</Empty> : <div className="sensor-list">{sensors.map(s => <article className="sensor-row" key={s.id}><div className="sensor-icon"><Radio size={21} /></div><div className="sensor-name"><h3>{s.name}</h3><span>{series.find(x => x.id === s.seriesId)?.name || 'Seria'}</span></div><div className="sensor-time"><span>Ostatni pomiar</span><strong>{s.lastMeasurementAt ? time(s.lastMeasurementAt, true) : 'Jeszcze nie odebrano'}</strong></div><span className="registered"><span className="status-dot" />Zarejestrowany</span><button className="icon-btn delete-btn" aria-label={`Wyrejestruj czujnik ${s.name}`} onClick={() => setModal({ type: 'delete', target: { type: 'sensors', item: s } })}><Trash2 size={18} /></button></article>)}</div>}
        <div className="help-strip"><Leaf size={20} /><p>Jeden czujnik, jedna seria. Klucz pojawia się tylko podczas rejestracji. Wyrejestrowanie czujnika zachowuje wszystkie jego pomiary.</p></div>
      </section>}
      <footer><div className="inline"><Leaf size={16} /><strong>splot.</strong><span>Małe pomiary. Szersza perspektywa.</span></div><span>Obserwatorium mikroklimatu · ZAI 26Z</span></footer>
    </main>
    {modal?.type === 'login' && <LoginForm onClose={close} onLogin={(t, u) => { setToken(t); setUsername(u); if (modal.next) setView(modal.next); close(); setNotice('Zalogowano. Możesz zarządzać obserwatorium.'); }} />}
    {modal?.type === 'series' && token && <SeriesEditor current={modal.current} token={token} onClose={close} onSaved={saved} onError={authError} />}
    {modal?.type === 'sensor' && token && <SensorEditor series={series} token={token} onClose={close} onSaved={refresh} onError={authError} />}
    {modal?.type === 'password' && token && <PasswordEditor token={token} onClose={close} onError={authError} onSaved={() => { setToken(null); close(); setView('overview'); setNotice('Hasło zmienione. Zaloguj się nowym hasłem.'); }} />}
    {modal?.type === 'delete' && token && <DeleteDialog target={modal.target} token={token} onClose={close} onSaved={saved} onError={authError} />}
  </>;
}

createRoot(document.getElementById('root')).render(<App />);
