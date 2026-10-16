import { Box, Button, Chip, Typography } from '@mui/material';
import ArrowForward from '@mui/icons-material/ArrowForward';
import VideocamOutlined from '@mui/icons-material/VideocamOutlined';
import { Link } from 'react-router-dom';
import { useIncidents } from '../context/IncidentContext';
import { cameraSources, defaultFilters, filterIncidents } from '../utils/incidents';
import { DataBoundary, EmptyState, Metrics, PageHeader, Panel } from '../components/Common';
import { ActivityChart, CategoryChart, ReviewChart } from '../components/Charts';
import IncidentTable from '../components/IncidentTable';
export default function Dashboard() {
  const { incidents, health, checkedAt } = useIncidents();
  const recent = filterIncidents(incidents, defaultFilters).slice(0, 5);
  const sources = cameraSources(incidents);
  return <><PageHeader title="Operations overview" description="A clear view of your incidents. A focused path to action." action={<Button component={Link} to="/incidents?review=unreviewed" variant="contained" endIcon={<ArrowForward sx={{ fontSize: 16 }} />}>Review incidents</Button>} />
    <DataBoundary><Metrics /><div className="chart-grid"><ActivityChart incidents={incidents} /><CategoryChart incidents={incidents} /></div>
      <Panel title="Recent incidents" subtitle="Latest detections, ordered by event time" action={<Button component={Link} to="/incidents" size="small" endIcon={<ArrowForward sx={{ fontSize: 15 }} />}>View all</Button>}>
        {recent.length ? <IncidentTable incidents={recent} compact /> : <EmptyState title="Your incident queue is clear" description="Incidents from the vision pipeline will appear here once they are recorded by the backend." />}
      </Panel>
      <div className="bottom-grid"><ReviewChart incidents={incidents} /><Panel title="Camera monitoring" subtitle="Sources observed in incident records" action={<Button component={Link} to="/cameras" size="small" endIcon={<ArrowForward sx={{ fontSize: 15 }} />}>Cameras</Button>}>
        <Box sx={{ px: 2.75, pb: 2 }}>{sources.length ? sources.slice(0, 3).map(c => <div className="source-row" key={c.name}><span className="source-icon"><VideocamOutlined fontSize="small" /></span><div><Typography sx={{ fontSize: 12, fontWeight: 600 }}>{c.name}</Typography><Typography variant="caption" color="text.secondary">{c.count} recorded {c.count === 1 ? 'incident' : 'incidents'}</Typography></div><Chip label="Status unknown" variant="outlined" sx={{ ml: 'auto', fontSize: 10, color: 'text.secondary' }} /></div>) : <Typography variant="body2" color="text.secondary" sx={{ pb: 2 }}>No camera sources recorded yet.</Typography>}<Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>Live feeds and camera health are not supplied by this backend.</Typography></Box>
      </Panel></div>
      <Box sx={{ mt: 2.5, px: 2, py: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 2, display: 'flex', gap: 1, alignItems: 'center', bgcolor: '#F9FBFD', flexWrap: 'wrap' }}><span style={{ width: 6, height: 6, borderRadius: '50%', background: health === 'connected' ? '#22C55E' : '#F59E0B' }} /><Typography variant="caption" fontWeight={600}>Backend {health === 'connected' ? 'connected' : 'health unavailable'}</Typography><Typography variant="caption" color="text.secondary">{checkedAt ? `Checked ${checkedAt.toLocaleTimeString()}` : 'Awaiting health check'} · Refresh to retrieve new events.</Typography></Box>
    </DataBoundary></>;
}
