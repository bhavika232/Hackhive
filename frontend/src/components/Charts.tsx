import { Box } from '@mui/material';
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Incident } from '../services/api';
import { categoryLabels, confidenceDistribution, dailyActivity, groupCounts, reviewLabels } from '../utils/incidents';
import { EmptyState, Panel } from './Common';
const colors = ['#06B6D4', '#627DAB', '#A8BDD4', '#74B6A1', '#B5A1C7'];
const tooltipStyle = { border: '1px solid #E2E8F0', borderRadius: 8, fontSize: 12, boxShadow: '0 4px 20px #1723380D' };
export function CountChart({ data, horizontal = false }: { data: { name: string; count: number }[]; horizontal?: boolean }) {
  if (!data.some(d => d.count > 0)) return <EmptyState title="No data to chart" description="This chart will populate when matching incidents are available." />;
  return <div className="chart-area" style={horizontal ? { height: Math.max(230, data.length * 40 + 40) } : undefined}><ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout={horizontal ? 'vertical' : 'horizontal'} margin={{ top: 12, right: 16, bottom: 4, left: horizontal ? 10 : -20 }} accessibilityLayer>
    <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="#ECF0F5" />
    <XAxis type={horizontal ? 'number' : 'category'} dataKey={horizontal ? undefined : 'name'} allowDecimals={false} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#8492A6' }} dy={6} minTickGap={22} />
    <YAxis type={horizontal ? 'category' : 'number'} dataKey={horizontal ? 'name' : undefined} allowDecimals={false} axisLine={false} tickLine={false} width={horizontal ? 100 : 50} tick={{ fontSize: 10, fill: '#8492A6' }} />
    <Tooltip cursor={{ fill: '#F5F9FC' }} contentStyle={tooltipStyle} /><Bar dataKey="count" name="Incidents" fill="#06B6D4" radius={horizontal ? [0, 3, 3, 0] : [3, 3, 0, 0]} maxBarSize={38} isAnimationActive={false} />
  </BarChart></ResponsiveContainer></div>;
}
export function ActivityChart({ incidents }: { incidents: Incident[] }) {
  const data = dailyActivity(incidents);
  return <Panel title="Incident activity" subtitle="Daily counts on recorded dates · local time" action={<span className="chart-legend"><i />Incidents</span>}><CountChart data={data} /></Panel>;
}
export function CategoryChart({ incidents }: { incidents: Incident[] }) {
  const data = groupCounts(incidents, 'category', categoryLabels);
  return <Panel title="By category" subtitle="Distribution across all recorded incidents">{!data.length ? <EmptyState title="No categories yet" description="Category distribution appears after the first incident." /> : <Box sx={{ display: 'flex', alignItems: 'center', px: 2, pb: 2, minHeight: 230, flexWrap: { xs: 'wrap', sm: 'nowrap' } }}>
    <Box sx={{ width: '48%', minWidth: 140, height: 200, position: 'relative' }}><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data} dataKey="count" nameKey="name" innerRadius="65%" outerRadius="88%" paddingAngle={data.length > 1 ? 4 : 0} stroke="none" isAnimationActive={false}>{data.map((d, idx) => <Cell key={d.name} fill={colors[idx % colors.length]} />)}</Pie><Tooltip contentStyle={tooltipStyle} /></PieChart></ResponsiveContainer><Box sx={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', pointerEvents: 'none' }}><strong style={{ fontSize: 26, fontWeight: 650 }}>{incidents.length}</strong><span style={{ fontSize: 10, color: '#8492A6' }}>incidents</span></Box></Box>
    <Box sx={{ flex: 1, pl: 1.5 }}>{data.map((d, idx) => <Box key={d.name} sx={{ display: 'flex', alignItems: 'center', gap: 1, my: 2.5, fontSize: 11 }}><Box sx={{ width: 7, height: 7, borderRadius: '2px', bgcolor: colors[idx % colors.length], flexShrink: 0 }} /><span style={{ color: '#64748B' }}>{d.name}</span><strong style={{ marginLeft: 'auto' }}>{d.count}</strong></Box>)}</Box>
  </Box>}</Panel>;
}
export function ReviewChart({ incidents }: { incidents: Incident[] }) {
  const colors: Record<string, string> = { unreviewed: '#E8B34F', true_positive: '#43A57C', false_positive: '#A8B7CB' };
  return <Panel title="Review progress" subtitle="Operator decisions, separate from detection confidence"><Box sx={{ px: 3, pb: 1 }}>{Object.entries(reviewLabels).map(([key, name]) => {
    const count = incidents.filter(i => i.review_status === key).length;
    return <div className="review-row" key={key}><span>{name}</span><div className="review-track"><i style={{ width: `${incidents.length ? count / incidents.length * 100 : 0}%`, background: colors[key] }} /></div><strong style={{ textAlign: 'right', color: '#334155' }}>{count}</strong></div>;
  })}{!incidents.length && <p className="panel-subtitle" style={{ marginBottom: 18 }}>No incidents have been recorded.</p>}</Box></Panel>;
}
export function ConfidenceChart({ incidents }: { incidents: Incident[] }) { return <Panel title="Detection confidence" subtitle="Backend confidence scores · not a measure of accuracy"><CountChart data={confidenceDistribution(incidents)} /></Panel>; }
