import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import {
  Category,
  defaultApiBase,
  getApiBase,
  getHealth,
  getIncident,
  getIncidents,
  Incident,
  ReviewStatus,
  updateReview,
} from './api'

type Page = 'overview' | 'monitor' | 'incidents' | 'analytics' | 'system' | 'settings'
type IconName = 'overview' | 'monitor' | 'incidents' | 'analytics' | 'system' | 'settings' | 'search' | 'refresh' | 'arrow' | 'eye' | 'clock' | 'close' | 'external' | 'video' | 'camera' | 'activity' | 'copy'

const pages: { id: Page; label: string; icon: IconName }[] = [
  { id: 'overview', label: 'Overview', icon: 'overview' },
  { id: 'monitor', label: 'Live Monitoring', icon: 'monitor' },
  { id: 'incidents', label: 'Incidents', icon: 'incidents' },
  { id: 'analytics', label: 'Analytics', icon: 'analytics' },
  { id: 'system', label: 'Model & System', icon: 'system' },
  { id: 'settings', label: 'Settings', icon: 'settings' },
]

const categories: Category[] = ['person_down', 'tailgating', 'crowd_incident']
const categoryNames: Record<Category, string> = {
  person_down: 'Person down', tailgating: 'Tailgating', crowd_incident: 'Crowd incident',
}
const reviewNames: Record<ReviewStatus, string> = {
  unreviewed: 'Unreviewed', true_positive: 'True positive', false_positive: 'False positive',
}

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, ReactNode> = {
    overview: <><rect x="3" y="3" width="8" height="8" rx="2"/><rect x="14" y="3" width="7" height="5" rx="2"/><rect x="14" y="11" width="7" height="10" rx="2"/><rect x="3" y="14" width="8" height="7" rx="2"/></>,
    monitor: <><rect x="3" y="4" width="18" height="14" rx="3"/><path d="M8 21h8M12 18v3M10 10l3 2-3 2z"/></>,
    incidents: <><path d="M12 3 21 19H3L12 3Z"/><path d="M12 9v4m0 3h.01"/></>,
    analytics: <><path d="M4 19V5m0 14h17"/><path d="m7 15 4-4 3 2 5-6"/></>,
    system: <><rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01M11 7h6m-6 10h6"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1a1.8 1.8 0 1 1-2.5 2.5l-.1-.1a1.8 1.8 0 0 0-3 .9v.2a1.8 1.8 0 1 1-3.6 0v-.2a1.8 1.8 0 0 0-3-.9l-.1.1a1.8 1.8 0 1 1-2.5-2.5l.1-.1a1.8 1.8 0 0 0-.9-3h-.2a1.8 1.8 0 1 1 0-3.6h.2a1.8 1.8 0 0 0 .9-3l-.1-.1a1.8 1.8 0 1 1 2.5-2.5l.1.1a1.8 1.8 0 0 0 3-.9v-.2a1.8 1.8 0 1 1 3.6 0v.2a1.8 1.8 0 0 0 3 .9l.1-.1a1.8 1.8 0 1 1 2.5 2.5l-.1.1a1.8 1.8 0 0 0 .9 3h.2a1.8 1.8 0 1 1 0 3.6h-.2a1.8 1.8 0 0 0-.9 3Z"/></>,
    search: <><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></>,
    refresh: <><path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.5 9a7 7 0 0 1 12-2L20 12M4 12l2.5 5a7 7 0 0 0 12-2"/></>,
    arrow: <><path d="M5 12h14m-6-6 6 6-6 6"/></>,
    eye: <><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    close: <><path d="m6 6 12 12M18 6 6 18"/></>,
    external: <><path d="M14 4h6v6m-11 5L20 4"/><path d="M18 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h6"/></>,
    video: <><rect x="3" y="5" width="13" height="14" rx="3"/><path d="m16 10 5-3v10l-5-3z"/></>,
    camera: <><path d="M4 7h3l2-2h6l2 2h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z"/><circle cx="12" cy="13" r="3"/></>,
    activity: <><path d="M3 12h4l3-8 4 16 3-8h4"/></>,
    copy: <><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></>,
  }
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>
}

function labelCategory(category: Category) { return categoryNames[category] ?? category }
function formatTime(value?: string | null) {
  if (!value) return 'Time unavailable'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
}
function relativeTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Time unavailable'
  const seconds = Math.round((date.getTime() - Date.now()) / 1000)
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
  if (Math.abs(seconds) < 60) return rtf.format(seconds, 'second')
  if (Math.abs(seconds) < 3600) return rtf.format(Math.round(seconds / 60), 'minute')
  if (Math.abs(seconds) < 86400) return rtf.format(Math.round(seconds / 3600), 'hour')
  return rtf.format(Math.round(seconds / 86400), 'day')
}
function categoryClass(category: Category) { return category.replace('_', '-') }
function confidenceText(value: number) { return `${Math.round(value * 100)}%` }
function todayCount(items: Incident[]) {
  const now = new Date()
  return items.filter((item) => {
    const date = new Date(item.start_wall_time)
    return !Number.isNaN(date.getTime()) && date.toDateString() === now.toDateString()
  }).length
}

function App() {
  const [page, setPage] = useState<Page>(() => pageFromHash())
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [health, setHealth] = useState<'checking' | 'connected' | 'disconnected'>('checking')
  const [loading, setLoading] = useState(true)
  const [incidentError, setIncidentError] = useState('')
  const [healthError, setHealthError] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [apiBase, setApiBase] = useState(getApiBase())
  const [selected, setSelected] = useState<Incident | null>(null)
  const [analysisOpen, setAnalysisOpen] = useState(false)
  const [searchId, setSearchId] = useState('')
  const [jumpError, setJumpError] = useState('')
  const [reviewBusy, setReviewBusy] = useState(false)
  const [reviewError, setReviewError] = useState('')
  const [toast, setToast] = useState('')

  const refresh = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true)
    const [healthResult, incidentsResult] = await Promise.allSettled([getHealth(), getIncidents()])
    if (healthResult.status === 'fulfilled') {
      setHealth('connected'); setHealthError('')
    } else {
      setHealth('disconnected'); setHealthError(errorMessage(healthResult.reason))
    }
    if (incidentsResult.status === 'fulfilled') {
      setIncidents(incidentsResult.value); setIncidentError(''); setLastUpdated(new Date())
    } else {
      setIncidentError(errorMessage(incidentsResult.reason))
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    const onHash = () => setPage(pageFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    let active = true
    let timer = 0
    const poll = async () => {
      await refresh(true)
      if (active) timer = window.setTimeout(poll, 30000)
    }
    void poll()
    return () => { active = false; window.clearTimeout(timer) }
  }, [refresh, apiBase])

  useEffect(() => {
    if (!toast) return
    const timer = window.setTimeout(() => setToast(''), 2600)
    return () => window.clearTimeout(timer)
  }, [toast])

  const cameraIds = useMemo(() => [...new Set(incidents.map((item) => item.camera_id))].sort(), [incidents])
  const title = pages.find((item) => item.id === page)?.label ?? 'Overview'
  const newest = incidents[0]

  function navigate(next: Page) {
    window.location.hash = `/${next}`
    setPage(next)
  }

  async function jumpToIncident(event: FormEvent) {
    event.preventDefault()
    const id = Number(searchId)
    if (!Number.isInteger(id) || id <= 0) { setJumpError('Enter a valid incident ID.'); return }
    setJumpError('')
    try {
      const incident = incidents.find((item) => item.incident_id === id) ?? await getIncident(id)
      setSelected(incident)
    } catch (error) { setJumpError(errorMessage(error)) }
  }

  async function saveReview(status: ReviewStatus) {
    if (!selected) return
    setReviewBusy(true); setReviewError('')
    try {
      const updated = await updateReview(selected.incident_id, status)
      setSelected(updated)
      setIncidents((items) => items.map((item) => item.incident_id === updated.incident_id ? updated : item))
      setToast(`Incident #${updated.incident_id} marked ${reviewNames[updated.review_status]}.`)
    } catch (error) { setReviewError(errorMessage(error)) }
    finally { setReviewBusy(false) }
  }

  function saveBase(value: string) {
    const clean = value.trim().replace(/\/$/, '')
    if (!/^https?:\/\//.test(clean)) return 'Enter a valid http:// or https:// API base URL.'
    localStorage.setItem('sentinel.apiBase', clean)
    setApiBase(clean)
    return ''
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#/overview" onClick={() => navigate('overview')}>
        <span className="brand-mark"><Icon name="eye" size={20}/></span>
        <span><b>SENTINEL <em>AI</em></b><small>SEE BEYOND THE FRAME</small></span>
      </a>
      <div className="side-caption">WORKSPACE</div>
      <nav className="side-nav" aria-label="Main navigation">
        {pages.map((item) => <a key={item.id} href={`#/${item.id}`} aria-label={item.label} title={item.label} className={`nav-link ${page === item.id ? 'active' : ''}`} onClick={() => navigate(item.id)}>
          <Icon name={item.icon}/><span>{item.label}</span>{page === item.id && <span className="nav-active-mark"/>}
        </a>)}
      </nav>
      <div className="sidebar-spacer"/>
      <div className="sidebar-status">
        <div className="status-heading"><span className={`status-dot ${health}`}/><span>BACKEND STATUS</span><button className="icon-button tiny" onClick={() => void refresh()} aria-label="Retry backend"><Icon name="refresh" size={14}/></button></div>
        <strong>{health === 'connected' ? 'Systems operational' : health === 'checking' ? 'Connecting…' : 'Connection lost'}</strong>
        <small>{health === 'connected' ? 'Local API is responding' : healthError || 'Checking local API'}</small>
      </div>
      <div className="operator"><div className="avatar">BH</div><div><b>Security operator</b><small>Local workspace</small></div><span className="operator-menu">•••</span></div>
    </aside>

    <main className="main-area">
      <header className="topbar">
        <div className="breadcrumbs"><span>SENTINEL</span><i>/</i><strong>{title}</strong></div>
        <div className="topbar-actions">
          <form className="jump-search" onSubmit={jumpToIncident}>
            <Icon name="search" size={16}/><input value={searchId} onChange={(e) => setSearchId(e.target.value)} aria-label="Jump to incident ID" placeholder="Jump to incident…"/><kbd>↵</kbd>
            {jumpError && <span className="search-error">{jumpError}</span>}
          </form>
          <span className={`connection-pill ${health}`}><span className="status-dot"/>{health === 'connected' ? 'CONNECTED' : health === 'checking' ? 'CHECKING' : 'DISCONNECTED'}</span>
          <span className="local-clock"><Icon name="clock" size={15}/>{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          <div className="top-avatar">BH</div>
        </div>
      </header>

      {(health === 'disconnected' || incidentError) && <div className="error-banner"><span>{health === 'disconnected' ? `Backend disconnected: ${healthError}` : `Incident data unavailable: ${incidentError}`}</span><button className="button button-small" onClick={() => void refresh(true)}><Icon name="refresh" size={14}/> Retry</button></div>}

      <section className="content">
        {page === 'overview' && <Overview incidents={incidents} cameraIds={cameraIds} health={health} loading={loading} lastUpdated={lastUpdated} onNavigate={navigate} onSelect={setSelected} onAnalysis={() => setAnalysisOpen(true)} onRefresh={() => void refresh(true)} incidentError={incidentError}/>}
        {page === 'monitor' && <Monitor incidents={incidents} cameraIds={cameraIds} onSelect={setSelected} onAnalysis={() => setAnalysisOpen(true)} loading={loading}/>}
        {page === 'incidents' && <IncidentsPage incidents={incidents} loading={loading} error={incidentError} onSelect={setSelected} onRefresh={() => void refresh(true)}/>}
        {page === 'analytics' && <Analytics incidents={incidents} loading={loading}/>}
        {page === 'system' && <SystemPage health={health} healthError={healthError} apiBase={apiBase} lastUpdated={lastUpdated} onRefresh={() => void refresh(true)}/>}
        {page === 'settings' && <Settings apiBase={apiBase} onSave={saveBase} onRefresh={() => void refresh(true)} onToast={setToast}/>}
      </section>
      <footer className="footer"><span>© 2026 SENTINEL AI</span><span>LOCAL SECURITY OPERATIONS <i>·</i> DATA FROM YOUR BACKEND</span></footer>
    </main>

    {selected && <IncidentDialog incident={selected} busy={reviewBusy} error={reviewError} onClose={() => { setSelected(null); setReviewError('') }} onReview={saveReview}/>}
    {analysisOpen && <AnalysisDialog cameras={cameraIds} onClose={() => setAnalysisOpen(false)} onToast={setToast}/>}
    {toast && <div className="toast" role="status">{toast}</div>}
  </div>
}

function pageFromHash(): Page {
  const key = window.location.hash.replace(/^#\/?/, '').split('/')[0] as Page
  return pages.some((item) => item.id === key) ? key : 'overview'
}
function errorMessage(error: unknown) { return error instanceof Error ? error.message : 'An unexpected error occurred.' }

function Eyebrow({ children }: { children: ReactNode }) { return <div className="eyebrow">{children}</div> }
function SectionTitle({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: ReactNode }) {
  return <div className="section-title"><div>{eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}<h2>{title}</h2></div>{action}</div>
}
function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon"><Icon name="activity" size={22}/></div><strong>{title}</strong><p>{body}</p>{action}</div>
}
function BackendBadge({ state }: { state: string }) {
  return <span className={`backend-badge ${state}`}><span className="status-dot"/>{state === 'connected' ? 'Backend connected' : state === 'checking' ? 'Checking backend' : 'Backend disconnected'}</span>
}
function IncidentChip({ category }: { category: Category }) { return <span className={`category-chip ${categoryClass(category)}`}><i/>{labelCategory(category)}</span> }
function ReviewChip({ status }: { status: ReviewStatus }) { return <span className={`review-chip ${status.replace('_', '-')}`}>{reviewNames[status] ?? status}</span> }

function Overview({ incidents, cameraIds, health, loading, lastUpdated, onNavigate, onSelect, onAnalysis, onRefresh, incidentError }: {
  incidents: Incident[]; cameraIds: string[]; health: string; loading: boolean; lastUpdated: Date | null; onNavigate: (page: Page) => void; onSelect: (item: Incident) => void; onAnalysis: () => void; onRefresh: () => void; incidentError: string
}) {
  const today = todayCount(incidents)
  return <>
    <section className="hero-panel">
      <div className="hero-grid"/>
      <div className="hero-copy">
        <Eyebrow><span className="eyebrow-spark"/> SENTINEL AI <i>/</i> SECURITY OPERATIONS</Eyebrow>
        <h1>Your environment,<br/><span>understood in real time.</span></h1>
        <p>AI-powered video intelligence for faster, smarter incident detection.</p>
        <div className="hero-state"><BackendBadge state={health}/><span>See Beyond the Frame.</span><button className="text-button connection-action" onClick={onRefresh}><Icon name="refresh" size={13}/> Check connection</button></div>
        <div className="hero-actions"><button className="button button-primary" onClick={() => onNavigate('monitor')}><Icon name="monitor" size={16}/> Open Live Monitor <Icon name="arrow" size={15}/></button><button className="button button-secondary" onClick={onAnalysis}><Icon name="video" size={16}/> Run Video Analysis</button></div>
      </div>
      <div className="hero-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="scan-frame"><div className="scan-crosshair">⌖</div><div className="scan-label">LOCAL · VISION PIPELINE</div><div className="scan-lines"/></div><div className="art-node node-a"/><div className="art-node node-b"/><div className="art-node node-c"/></div>
      <div className="hero-foot"><span><span className="status-dot connected"/> LOCAL EVENT INTELLIGENCE</span><span>{lastUpdated ? `LAST SYNC ${lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'WAITING FOR FIRST SYNC'}</span></div>
    </section>

    <div className="metric-grid">
      <Metric label="ACTIVE CAMERAS" value="Not available" detail="Camera connectivity is not exposed by the API" icon="camera" tint="purple"/>
      <Metric label="INCIDENTS TODAY" value={loading && !incidents.length ? '—' : String(today)} detail="From stored event timestamps, local time" icon="incidents" tint="pink"/>
      <Metric label="PEOPLE DETECTED" value="Not available" detail="The incidents API does not return detection totals" icon="activity" tint="blue"/>
      <Metric label="SYSTEM HEALTH" value={health === 'connected' ? 'Operational' : health === 'checking' ? 'Checking' : 'Disconnected'} detail={health === 'connected' ? 'Verified through GET /health' : 'Verified through GET /health'} icon="system" tint={health === 'connected' ? 'teal' : 'amber'}/>
    </div>

    <div className="section-layout">
      <section className="panel primary-view">
        <SectionTitle eyebrow="SOURCE STATUS" title="Primary view" action={<span className="live-label"><i/> NO LIVE STREAM</span>}/>
        <div className="monitor-empty"><div className="view-grid"/><div className="monitor-emblem"><Icon name="video" size={28}/></div><div className="monitor-status">NO ACTIVE VIDEO SOURCE</div><h3>Nothing connected right now</h3><p>The API has no live-stream endpoint. Use the local analysis workflow to process a video file.</p><button className="text-button" onClick={onAnalysis}>Open video analysis guide <Icon name="arrow" size={15}/></button></div>
        <div className="source-meta"><span><small>OBSERVED CAMERAS</small><b>{cameraIds.length ? cameraIds.join(', ') : 'None in incident records'}</b></span><span><small>RECORDED INCIDENTS</small><b>{incidents.length}</b></span><span><small>SOURCE</small><b>Local API</b></span></div>
      </section>
      <section className="panel activity-panel">
        <SectionTitle eyebrow="REAL-TIME FEED" title="Incident activity" action={<button className="icon-button" onClick={onRefresh} aria-label="Refresh incidents"><Icon name="refresh"/></button>}/>
        {incidentError ? <EmptyState title="Activity unavailable" body={incidentError}/> : loading && !incidents.length ? <LoadingRows/> : incidents.length ? <div className="activity-list">{incidents.slice(0, 6).map((item) => <IncidentRow key={item.incident_id} incident={item} onClick={() => onSelect(item)}/>)}</div> : <EmptyState title="No incidents recorded" body="New incidents appear here after the vision pipeline sends them to the backend."/>}
        <button className="panel-link" onClick={() => onNavigate('incidents')}>View all incidents <Icon name="arrow" size={15}/></button>
      </section>
    </div>

    <Timeline incidents={incidents}/>
    <section className="camera-section">
      <SectionTitle eyebrow="DERIVED FROM STORED EVENTS" title="Cameras observed in incident records" action={<span className="muted-note">Historical IDs · not live connectivity</span>}/>
      {cameraIds.length ? <div className="camera-grid">{cameraIds.map((camera) => <CameraCard key={camera} camera={camera} incidents={incidents.filter((item) => item.camera_id === camera)}/>)}</div> : <EmptyState title="No camera identifiers yet" body="Camera cards are derived from camera IDs on stored incidents."/>}
    </section>
  </>
}

function Metric({ label, value, detail, icon, tint }: { label: string; value: string; detail: string; icon: IconName; tint: string }) {
  return <article className="metric-card"><div className={`metric-icon ${tint}`}><Icon name={icon}/></div><span className="metric-label">{label}</span><strong className={value === 'Not available' ? 'metric-unavailable' : ''}>{value}</strong><small>{detail}</small></article>
}
function LoadingRows() { return <div className="loading-rows"><i/><i/><i/></div> }
function IncidentRow({ incident, onClick }: { incident: Incident; onClick: () => void }) {
  return <button className="activity-row" onClick={onClick}><span className={`activity-icon ${categoryClass(incident.category)}`}><Icon name={incident.category === 'person_down' ? 'incidents' : incident.category === 'tailgating' ? 'arrow' : 'activity'} size={16}/></span><span className="activity-main"><span className="activity-top"><IncidentChip category={incident.category}/><small>#{incident.incident_id}</small></span><strong>{incident.summary}</strong><small>{incident.camera_id} <i>·</i> {relativeTime(incident.start_wall_time)}</small></span><span className="activity-confidence">{confidenceText(incident.confidence)}</span></button>
}

function Timeline({ incidents }: { incidents: Incident[] }) {
  const [range, setRange] = useState<'6h' | '24h' | '7d'>('24h')
  const now = Date.now()
  const span = range === '6h' ? 6 * 3600000 : range === '24h' ? 24 * 3600000 : 7 * 86400000
  const bucketsCount = range === '6h' ? 12 : range === '24h' ? 12 : 7
  const bucketMs = span / bucketsCount
  const buckets = Array.from({ length: bucketsCount }, (_, index) => ({ at: now - span + index * bucketMs, counts: { person_down: 0, tailgating: 0, crowd_incident: 0 } }))
  let available = 0
  for (const incident of incidents) {
    const time = new Date(incident.start_wall_time).getTime()
    if (!Number.isFinite(time) || time < now - span || time > now) continue
    available += 1
    const index = Math.min(bucketsCount - 1, Math.floor((time - (now - span)) / bucketMs))
    buckets[index].counts[incident.category] += 1
  }
  const max = Math.max(1, ...buckets.map((bucket) => categories.reduce((sum, category) => sum + bucket.counts[category], 0)))
  const axisLabel = (time: number) => new Date(time).toLocaleTimeString([], { hour: 'numeric', ...(range === '7d' ? {} : { minute: '2-digit' }) })
  return <section className="panel timeline-panel"><div className="timeline-heading"><div><Eyebrow>EVENT DISTRIBUTION</Eyebrow><h2>Incident timeline</h2><p>Based on stored event timestamps · shown in your local time</p></div><div className="range-tabs">{(['6h', '24h', '7d'] as const).map((value) => <button key={value} className={range === value ? 'selected' : ''} onClick={() => setRange(value)}>{value}</button>)}</div></div>
    {available ? <><div className="timeline-chart">{buckets.map((bucket, index) => <div className="chart-column" key={index}><div className="bar-stack" title={categories.map((category) => `${labelCategory(category)}: ${bucket.counts[category]}`).join(' · ')}>{categories.map((category) => { const count = bucket.counts[category]; return count ? <i key={category} className={`bar-segment ${categoryClass(category)}`} style={{ height: `${Math.max(5, count / max * 100)}%` }}/> : null })}</div><small>{index % (range === '7d' ? 1 : 2) === 0 ? axisLabel(bucket.at) : ''}</small></div>)}</div><div className="timeline-legend">{categories.map((category) => <span key={category}><i className={categoryClass(category)}/>{labelCategory(category)}</span>)}</div></> : <div className="timeline-empty"><Icon name="activity" size={20}/><span>No timestamped incidents in the selected range.</span></div>}
  </section>
}

function CameraCard({ camera, incidents }: { camera: string; incidents: Incident[] }) {
  const sorted = [...incidents].sort((a, b) => new Date(b.start_wall_time).getTime() - new Date(a.start_wall_time).getTime())
  const last = sorted[0]
  return <article className="camera-card"><div className="camera-card-top"><span className="camera-symbol"><Icon name="camera" size={17}/></span><span className="camera-record-label">RECORDED ID</span></div><strong>{camera}</strong><div className="camera-card-bottom"><span>{incidents.length} incident{incidents.length === 1 ? '' : 's'}</span><span>{last ? labelCategory(last.category) : '—'}</span></div><small>{last ? `Last recorded ${formatTime(last.start_wall_time)}` : 'No event time available'}</small></article>
}

function Monitor({ incidents, cameraIds, onSelect, onAnalysis, loading }: { incidents: Incident[]; cameraIds: string[]; onSelect: (item: Incident) => void; onAnalysis: () => void; loading: boolean }) {
  const [camera, setCamera] = useState('all')
  const filtered = camera === 'all' ? incidents : incidents.filter((item) => item.camera_id === camera)
  return <><PageHeading eyebrow="LIVE MONITORING" title="Monitor" subtitle="Live streams are not exposed by the current backend. Historical incident activity is available below."/>
    <div className="monitor-layout"><section className="panel monitor-large"><div className="monitor-empty large"><div className="view-grid"/><div className="monitor-emblem"><Icon name="video" size={30}/></div><div className="monitor-status">NO LIVE STREAM CONNECTED</div><h3>Monitoring source unavailable</h3><p>This backend has no camera-connectivity or live-video route. Recorded incident evidence remains available as a stored local path.</p><button className="button button-primary" onClick={onAnalysis}><Icon name="video" size={16}/> Open local analysis guide</button></div><div className="source-meta"><span><small>CAMERA IDS</small><b>{cameraIds.length ? cameraIds.join(', ') : 'None recorded'}</b></span><span><small>LIVE SOURCE</small><b>Not available</b></span><span><small>API STATUS</small><b>Incident records only</b></span></div></section>
      <section className="panel monitor-feed"><SectionTitle eyebrow="STORED ACTIVITY" title="Recent events" action={<select value={camera} onChange={(e) => setCamera(e.target.value)} aria-label="Filter camera"><option value="all">All cameras</option>{cameraIds.map((id) => <option key={id}>{id}</option>)}</select>}/>{loading && !filtered.length ? <LoadingRows/> : filtered.length ? <div className="activity-list scroll-list">{filtered.slice(0, 30).map((item) => <IncidentRow key={item.incident_id} incident={item} onClick={() => onSelect(item)}/>)}</div> : <EmptyState title="No recorded events" body="Incidents will appear here after they are stored by the backend."/>}</section></div>
    <Timeline incidents={filtered}/>
  </>
}

function PageHeading({ eyebrow, title, subtitle, action }: { eyebrow: string; title: string; subtitle: string; action?: ReactNode }) {
  return <div className="page-heading"><div><Eyebrow>{eyebrow}</Eyebrow><h1>{title}</h1><p>{subtitle}</p></div>{action}</div>
}

function IncidentsPage({ incidents, loading, error, onSelect, onRefresh }: { incidents: Incident[]; loading: boolean; error: string; onSelect: (item: Incident) => void; onRefresh: () => void }) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('all')
  const [review, setReview] = useState('all')
  const [sort, setSort] = useState<'time' | 'category' | 'confidence'>('time')
  const filtered = useMemo(() => incidents.filter((item) => {
    const text = `${item.incident_id} ${item.camera_id} ${item.category} ${item.summary}`.toLowerCase()
    return (!query || text.includes(query.toLowerCase())) && (category === 'all' || item.category === category) && (review === 'all' || item.review_status === review)
  }).sort((a, b) => sort === 'category' ? a.category.localeCompare(b.category) : sort === 'confidence' ? b.confidence - a.confidence : new Date(b.start_wall_time).getTime() - new Date(a.start_wall_time).getTime()), [incidents, query, category, review, sort])
  return <><PageHeading eyebrow="INCIDENT MANAGEMENT" title="Incidents" subtitle="Search and review incidents stored by the Sentinel backend." action={<button className="button button-secondary" onClick={onRefresh}><Icon name="refresh" size={15}/> Refresh records</button>}/>
    <section className="panel incidents-panel"><div className="filter-row"><label className="filter-search"><Icon name="search" size={16}/><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search ID, camera, category, summary…"/></label><select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Filter category"><option value="all">All categories</option>{categories.map((item) => <option key={item} value={item}>{labelCategory(item)}</option>)}</select><select value={review} onChange={(e) => setReview(e.target.value)} aria-label="Filter review status"><option value="all">All review states</option>{Object.entries(reviewNames).map(([value, name]) => <option key={value} value={value}>{name}</option>)}</select><select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)} aria-label="Sort incidents"><option value="time">Newest first</option><option value="category">Category</option><option value="confidence">Confidence</option></select></div>
      <div className="results-count"><span>{loading ? 'Loading records…' : `${filtered.length} incident${filtered.length === 1 ? '' : 's'}`}</span>{error && <span className="inline-error">{error}</span>}</div>
      {error ? <EmptyState title="Incident list unavailable" body={error} action={<button className="button button-secondary" onClick={onRefresh}>Retry</button>}/> : loading && !incidents.length ? <LoadingRows/> : filtered.length ? <div className="table-scroll"><table className="incident-table"><thead><tr><th>INCIDENT</th><th>EVENT</th><th>CAMERA</th><th>EVENT TIME</th><th>CONFIDENCE</th><th>REVIEW</th><th/></tr></thead><tbody>{filtered.map((item) => <tr key={item.incident_id} onClick={() => onSelect(item)} tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter') onSelect(item) }}><td><b>#{item.incident_id}</b><small>{item.track_ids.length ? `${item.track_ids.length} track${item.track_ids.length === 1 ? '' : 's'}` : 'No track IDs'}</small></td><td><IncidentChip category={item.category}/><small className="summary-cell">{item.summary}</small></td><td>{item.camera_id}</td><td>{formatTime(item.start_wall_time)}<small>{item.start_video_s.toFixed(1)}s into video</small></td><td><ConfidenceBar value={item.confidence}/></td><td><ReviewChip status={item.review_status}/></td><td><Icon name="arrow" size={16}/></td></tr>)}</tbody></table></div> : <EmptyState title={incidents.length ? 'No matching incidents' : 'No incidents recorded'} body={incidents.length ? 'Try changing or clearing your search and filters.' : 'The backend returned an empty incident list. New stored events will appear here.'}/>}</section>
  </>
}

function ConfidenceBar({ value }: { value: number }) { return <span className="confidence-wrap"><span className="confidence-track"><i style={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }}/></span><small>{confidenceText(value)}</small></span> }

function IncidentDialog({ incident, busy, error, onClose, onReview }: { incident: Incident; busy: boolean; error: string; onClose: () => void; onReview: (status: ReviewStatus) => void }) {
  useEffect(() => { const key = (event: KeyboardEvent) => event.key === 'Escape' && onClose(); window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key) }, [onClose])
  return <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}><section className="dialog incident-dialog" role="dialog" aria-modal="true" aria-labelledby="incident-dialog-title"><div className="dialog-header"><div><Eyebrow>INCIDENT RECORD · #{incident.incident_id}</Eyebrow><h2 id="incident-dialog-title">{labelCategory(incident.category)}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close incident details"><Icon name="close"/></button></div><div className="dialog-body"><div className="detail-highlight"><IncidentChip category={incident.category}/><ReviewChip status={incident.review_status}/><p>{incident.summary}</p></div><div className="detail-grid"><Detail label="Camera" value={incident.camera_id}/><Detail label="Event time" value={formatTime(incident.start_wall_time)}/><Detail label="Video offset" value={`${incident.start_video_s.toFixed(2)} seconds`}/><Detail label="Confidence" value={`${confidenceText(incident.confidence)} · ${incident.confidence_status.replace('_', ' ')}`}/><Detail label="Track IDs" value={incident.track_ids.length ? incident.track_ids.join(', ') : 'None recorded'}/><Detail label="Occurrences" value={String(incident.occurrence_count)}/><Detail label="End time" value={formatTime(incident.end_wall_time)}/></div><div className="evidence-block"><Eyebrow>KEYFRAME EVIDENCE</Eyebrow>{incident.keyframe_path ? <><code>{incident.keyframe_path}</code><p>Stored as a local filesystem path by the backend. No browser-accessible evidence route is available.</p></> : <p>No keyframe path was stored for this incident.</p>}</div>{error && <div className="inline-error">{error}</div>}</div><div className="dialog-footer"><span className="review-note">Review updates are saved to the backend.</span><button disabled={busy} className="button button-danger-soft" onClick={() => onReview('false_positive')}>{busy ? 'Saving…' : 'Mark false positive'}</button><button disabled={busy} className="button button-primary" onClick={() => onReview('true_positive')}>{busy ? 'Saving…' : 'Confirm incident'}</button></div></section></div>
}
function Detail({ label, value }: { label: string; value: string }) { return <div className="detail-item"><small>{label}</small><strong>{value}</strong></div> }

function Analytics({ incidents, loading }: { incidents: Incident[]; loading: boolean }) {
  const categoryCounts = categories.map((category) => ({ category, count: incidents.filter((item) => item.category === category).length }))
  const statuses = (Object.keys(reviewNames) as ReviewStatus[]).map((status) => ({ status, count: incidents.filter((item) => item.review_status === status).length }))
  const validTimes = incidents.filter((item) => Number.isFinite(new Date(item.start_wall_time).getTime())).length
  const averageConfidence = incidents.length ? incidents.reduce((sum, item) => sum + item.confidence, 0) / incidents.length : null
  return <><PageHeading eyebrow="INCIDENT INTELLIGENCE" title="Analytics" subtitle="Aggregates calculated from the backend incident list. No detections or history are simulated."/><div className="analytics-kpis"><Metric label="TOTAL INCIDENTS" value={loading ? '—' : String(incidents.length)} detail="Records returned by GET /incidents" icon="incidents" tint="purple"/><Metric label="UNREVIEWED" value={loading ? '—' : String(incidents.filter((item) => item.review_status === 'unreviewed').length)} detail="Current backend review state" icon="clock" tint="amber"/><Metric label="AVG. CONFIDENCE" value={averageConfidence === null ? 'Not available' : confidenceText(averageConfidence)} detail="Mean of stored confidence values" icon="analytics" tint="blue"/><Metric label="TIMESTAMP COVERAGE" value={incidents.length ? `${Math.round(validTimes / incidents.length * 100)}%` : 'Not available'} detail={`${validTimes} of ${incidents.length} have readable event times`} icon="activity" tint="teal"/></div>
    <div className="analytics-grid"><section className="panel analytics-panel"><SectionTitle eyebrow="CATEGORY BREAKDOWN" title="Incident categories"/>{incidents.length ? categoryCounts.map(({ category, count }) => <div className="breakdown-row" key={category}><div><IncidentChip category={category}/><b>{count}</b></div><span className="breakdown-track"><i className={categoryClass(category)} style={{ width: `${incidents.length ? count / incidents.length * 100 : 0}%` }}/></span><small>{incidents.length ? Math.round(count / incidents.length * 100) : 0}% of records</small></div>) : <EmptyState title="No category data" body="Category counts will appear when the API returns incidents."/>}</section><section className="panel analytics-panel"><SectionTitle eyebrow="REVIEW WORKFLOW" title="Review status"/>{incidents.length ? statuses.map(({ status, count }) => <div className="status-count-row" key={status}><ReviewChip status={status}/><b>{count}</b><span>{incidents.length ? `${Math.round(count / incidents.length * 100)}%` : '—'}</span></div>) : <EmptyState title="No review data" body="Review-state counts will appear when the API returns incidents."/>}</section></div><Timeline incidents={incidents}/></>
}

function SystemPage({ health, healthError, apiBase, lastUpdated, onRefresh }: { health: string; healthError: string; apiBase: string; lastUpdated: Date | null; onRefresh: () => void }) {
  return <><PageHeading eyebrow="RUNTIME STATUS" title="Model & System" subtitle="Live health comes from the backend. Model runtime status is not exposed by the current API." action={<button className="button button-secondary" onClick={onRefresh}><Icon name="refresh" size={15}/> Check status</button>}/><div className="system-grid"><section className="panel system-panel"><SectionTitle eyebrow="BACKEND" title="API service"/><div className="system-health"><BackendBadge state={health}/><p>{health === 'connected' ? 'The backend health endpoint responded successfully.' : health === 'checking' ? 'Waiting for a health response.' : healthError || 'The backend did not respond.'}</p></div><Detail label="Base URL" value={apiBase}/><Detail label="Health route" value="GET /health"/><Detail label="Incident route" value="GET /incidents"/><Detail label="Last successful data refresh" value={lastUpdated ? lastUpdated.toLocaleString() : 'Not yet refreshed'}/></section><section className="panel system-panel"><SectionTitle eyebrow="VISION PIPELINE" title="Configured models"/><ModelRow name="YOLOv8n" subtitle="Ultralytics/YOLOv8 · local detector and tracker" state="Configured in vision code; loaded state is not exposed by the API."/><ModelRow name="SmolVLM 256M" subtitle="HuggingFaceTB/SmolVLM-256M-Instruct · optional local verifier" state="Optional; requires cached weights and USE_VLM enabled for pipeline runs."/><div className="system-note">The pipeline runs as a separate local CLI process. This dashboard cannot start it or read its runtime state through the available backend routes.</div></section><section className="panel system-panel"><SectionTitle eyebrow="AVAILABLE WORKFLOWS" title="Backend capabilities"/><Capability name="Incident listing" method="GET /incidents"/><Capability name="Incident details" method="GET /incidents/{id}"/><Capability name="Review updates" method="PATCH /incidents/{id}/review"/><Capability name="Natural-language query" method="GET /query"/><Capability name="Video event ingestion" method="POST /ingest/vision-event"/><div className="system-note">No live-camera, streaming, evidence-file, or video-analysis launch endpoint is currently available.</div></section></div></>
}
function ModelRow({ name, subtitle, state }: { name: string; subtitle: string; state: string }) { return <div className="model-row"><span className="model-mark"><Icon name="activity" size={17}/></span><div><b>{name}</b><small>{subtitle}</small><p>{state}</p></div></div> }
function Capability({ name, method }: { name: string; method: string }) { return <div className="capability-row"><span>{name}</span><code>{method}</code></div> }

function Settings({ apiBase, onSave, onRefresh, onToast }: { apiBase: string; onSave: (value: string) => string; onRefresh: () => void; onToast: (value: string) => void }) {
  const [value, setValue] = useState(apiBase)
  const [error, setError] = useState('')
  useEffect(() => setValue(apiBase), [apiBase])
  function save(event: FormEvent) {
    event.preventDefault()
    const issue = onSave(value)
    setError(issue)
    if (!issue) onToast('API base URL saved. Reconnecting…')
  }
  return <><PageHeading eyebrow="PREFERENCES" title="Settings" subtitle="Configure this browser’s API connection. Changes are stored locally in this browser."/><div className="settings-grid"><form className="panel settings-panel" onSubmit={save}><SectionTitle eyebrow="CONNECTION" title="Backend API"/><label className="field-label" htmlFor="api-base">API base URL</label><input id="api-base" className="text-input" value={value} onChange={(e) => setValue(e.target.value)} placeholder={defaultApiBase}/><small className="field-help">VITE_API_BASE_URL provides the build-time default. This value overrides it in local browser storage.</small>{error && <div className="inline-error">{error}</div>}<div className="settings-actions"><button className="button button-primary" type="submit">Save API URL</button><button className="button button-secondary" type="button" onClick={onRefresh}>Test connection</button></div><button className="text-button reset-link" type="button" onClick={() => { localStorage.removeItem('sentinel.apiBase'); setValue(defaultApiBase); onSave(defaultApiBase); onToast('Default API URL restored.') }}>Restore configured default</button></form><section className="panel settings-panel"><SectionTitle eyebrow="LOCAL PREFERENCES" title="Data and privacy"/><div className="preference-item"><span><b>Incident refresh</b><small>Dashboard checks health and incident records every 30 seconds.</small></span><span className="preference-value">30 SEC</span></div><div className="preference-item"><span><b>Data source</b><small>All records are retrieved from your configured FastAPI backend.</small></span><span className="preference-value">LOCAL API</span></div><div className="preference-item"><span><b>Evidence access</b><small>Stored keyframe paths are displayed, not fetched as public URLs.</small></span><span className="preference-value">LOCAL PATH</span></div></section></div></>
}

function AnalysisDialog({ cameras, onClose, onToast }: { cameras: string[]; onClose: () => void; onToast: (value: string) => void }) {
  const [path, setPath] = useState('sample_videos\\fall_30fps.mp4')
  const [camera, setCamera] = useState('cam1')
  const command = `python run_pipeline.py "${path || '<video_path>'}" ${camera}`
  async function copy() {
    try { await navigator.clipboard.writeText(command); onToast('Command copied. Run it from the vision repository terminal.') }
    catch { onToast('Copy is unavailable in this browser. Select the command text instead.') }
  }
  return <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}><section className="dialog analysis-dialog" role="dialog" aria-modal="true" aria-labelledby="analysis-title"><div className="dialog-header"><div><Eyebrow>LOCAL VISION PIPELINE</Eyebrow><h2 id="analysis-title">Run video analysis</h2></div><button className="icon-button" onClick={onClose} aria-label="Close analysis guide"><Icon name="close"/></button></div><div className="dialog-body"><div className="analysis-notice"><span className="notice-icon"><Icon name="video"/></span><div><b>Analysis runs from the vision terminal</b><p>The backend has no route to launch video processing. This guide prepares the existing CLI command; selecting a browser file will not start analysis.</p></div></div><label className="field-label" htmlFor="video-path">Video path on the vision machine</label><input id="video-path" className="text-input" value={path} onChange={(e) => setPath(e.target.value)} placeholder="sample_videos\fall_30fps.mp4"/><label className="field-label" htmlFor="camera-id">Camera ID</label><input id="camera-id" className="text-input" list="camera-options" value={camera} onChange={(e) => setCamera(e.target.value)} placeholder="cam1"/><datalist id="camera-options">{cameras.map((id) => <option key={id} value={id}/>)}</datalist><div className="command-box"><code>$env:USE_VLM='0'; $env:HF_HUB_OFFLINE='1'; {command}</code><button className="icon-button" onClick={copy} aria-label="Copy command"><Icon name="copy" size={16}/></button></div><p className="field-help">Run from <code>Hackhive\hackhive-vision</code> with the vision virtual environment activated. Events are posted to the configured local backend.</p></div><div className="dialog-footer"><button className="button button-secondary" onClick={onClose}>Close</button><button className="button button-primary" onClick={copy}><Icon name="copy" size={15}/> Copy command</button></div></section></div>
}

export default App
