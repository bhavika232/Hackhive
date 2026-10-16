import type { ReactNode } from 'react';
import { Alert, Box, Button, Chip, Skeleton, Typography } from '@mui/material';
import Refresh from '@mui/icons-material/Refresh';
import InboxOutlined from '@mui/icons-material/InboxOutlined';
import ReportOutlined from '@mui/icons-material/ReportOutlined';
import Schedule from '@mui/icons-material/Schedule';
import TaskAlt from '@mui/icons-material/TaskAlt';
import VideocamOutlined from '@mui/icons-material/VideocamOutlined';
import { useIncidents } from '../context/IncidentContext';
import { cameraSources, label, reviewLabels, confidenceLabels } from '../utils/incidents';
export function PageHeader({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  const { refresh, loading, loadedAt } = useIncidents();
  return <div className="page-header"><div><div className="eyebrow">SENTINEL / OPERATIONS</div><Typography component="h1" variant="h4">{title}</Typography><p className="page-description">{description}</p></div>
    <div className="header-actions"><span className="header-timestamp">{loadedAt ? `Updated ${loadedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Waiting for data'}</span><Button variant="outlined" startIcon={<Refresh />} disabled={loading} onClick={refresh} sx={{ bgcolor: 'white', borderColor: 'divider', color: 'text.primary' }}>{loading ? 'Loading…' : 'Refresh'}</Button>{action}</div></div>;
}
export function EmptyState({ title, description, action, icon }: { title: string; description: string; action?: ReactNode; icon?: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon">{icon ?? <InboxOutlined />}</div><h3>{title}</h3><p>{description}</p>{action}</div>;
}
export function DataBoundary({ children }: { children: ReactNode }) {
  const { loading, error, refresh, healthError, loadedAt } = useIncidents();
  if (loading) return <Box role="status" aria-label="Loading incident data"><div className="metrics-grid">{[0, 1, 2, 3].map(i => <Skeleton key={i} variant="rounded" height={140} />)}</div><Skeleton variant="rounded" height={300} /></Box>;
  if (error) return <div className="panel"><EmptyState title="Incident data is unavailable" description={error} icon={<ReportOutlined />} action={<Button variant="contained" onClick={refresh}>Retry connection</Button>} />{loadedAt && <Typography align="center" variant="caption" color="text.secondary" sx={{ display: 'block', pb: 3 }}>Last successful load: {loadedAt.toLocaleString()}. Previous data is hidden until reconnection.</Typography>}</div>;
  return <>{healthError && <Alert severity="warning" sx={{ mb: 2 }} action={<Button onClick={refresh}>Retry</Button>}>Incidents loaded, but the backend health check failed. {healthError}</Alert>}{children}</>;
}
export function Metrics() {
  const { incidents } = useIncidents();
  const metrics = [
    { title: 'Total incidents', value: incidents.length, note: 'All recorded incidents', icon: <ReportOutlined />, color: '' },
    { title: 'Awaiting review', value: incidents.filter(i => i.review_status === 'unreviewed').length, note: 'Pending operator assessment', icon: <Schedule />, color: 'amber' },
    { title: 'Reviewed incidents', value: incidents.filter(i => i.review_status !== 'unreviewed').length, note: 'Includes false positives', icon: <TaskAlt />, color: 'green' },
    { title: 'Camera sources', value: cameraSources(incidents).length, note: 'Recorded sources · status unknown', icon: <VideocamOutlined />, color: 'slate' },
  ];
  return <div className="metrics-grid">{metrics.map(m => <article className="metric-card" key={m.title}><div className="metric-top"><span>{m.title}</span><span className={`metric-icon ${m.color}`}>{m.icon}</span></div><div className="metric-value">{m.value.toLocaleString()}</div><div className="metric-note">{m.note}</div></article>)}</div>;
}
export function Panel({ title, subtitle, action, children, className = '' }: { title: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><div className="panel-header"><div><h2 className="panel-title">{title}</h2>{subtitle && <p className="panel-subtitle">{subtitle}</p>}</div>{action}</div>{children}</section>;
}
export function ReviewBadge({ status }: { status?: string | null }) {
  const colors: Record<string, { color: string; bgcolor: string }> = { unreviewed: { color: '#A0660E', bgcolor: '#FFF5DF' }, true_positive: { color: '#237B52', bgcolor: '#EAF8EF' }, false_positive: { color: '#64748B', bgcolor: '#F0F3F7' } };
  return <Chip size="small" label={label(status, reviewLabels)} sx={colors[status ?? ''] ?? colors.false_positive} />;
}
export function ConfidenceBadge({ status }: { status?: string | null }) { return <Chip size="small" variant="outlined" label={label(status, confidenceLabels)} sx={{ color: status === 'confirmed' ? '#0E7490' : '#64748B', borderColor: '#E2E8F0', fontWeight: 500, fontSize: 10 }} />; }
